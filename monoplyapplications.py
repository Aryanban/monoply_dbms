import mysql.connector
from mysql.connector import Error
from typing import Optional, Tuple, List
import random
import re

class DatabaseConnection:
    def __init__(self, host: str = 'localhost', user: str = 'root', password: str = 'Sakai@2809', database: str = 'monopoly_db'):
        try:
            self.connection = mysql.connector.connect(
                host=host, user=user, password=password, database=database
            )
            self.connection.autocommit = False
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
            raise
    
    def get_cursor(self):
        return self.connection.cursor(dictionary=True)
    
    def commit(self):
        self.connection.commit()
    
    def rollback(self):
        self.connection.rollback()
    
    def close(self):
        if self.connection.is_connected():
            self.connection.close()


def start_game(db: DatabaseConnection) -> int:
    cursor = db.get_cursor()
    try:
        # Create the Game
        cursor.execute("SELECT COALESCE(MAX(game_id), 0) + 1 as next_id FROM game")
        game_id = cursor.fetchone()['next_id']
        cursor.execute("INSERT INTO game (game_id, status, created_at) VALUES (%s, 'running', NOW())", (game_id,))
        
        # Get starting ID for spaces
        cursor.execute("SELECT COALESCE(MAX(space_id), 0) + 1 as next_s_id FROM boardspace")
        next_s_id = cursor.fetchone()['next_s_id']
        
        # 1. Initialize 'GO' at Index 0
        cursor.execute("""
            INSERT INTO boardspace (space_id, name, index_no, type, game_id) 
            VALUES (%s, 'GO', 0, 'start', %s)
        """, (next_s_id, game_id))
        
        # 2. Initialize 'Jail' at Index 10
        cursor.execute("""
            INSERT INTO boardspace (space_id, name, index_no, type, game_id) 
            VALUES (%s, 'Just Visiting / Jail', 10, 'jail', %s)
        """, (next_s_id + 1, game_id))
        
        db.commit()
        print(f"✅ Game {game_id} started. 'GO' (Index 0) and 'Jail' (Index 10) initialized.")
        return game_id
    finally:
        cursor.close()

def register_player(db: DatabaseConnection, game_id: int, player_name: str) -> int:
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT COALESCE(MAX(player_id), 0) + 1 as next_id FROM player")
        next_id = cursor.fetchone()['next_id']
        cursor.execute("""
            INSERT INTO player (player_id, name, balance, position, inJail, jailTurns, isBankrupt, game_id)
            VALUES (%s, %s, 1500, 0, 0, 0, 0, %s)
        """, (next_id, player_name, game_id))
        db.commit()
        return next_id
    finally:
        cursor.close()

def update_player_balance(db: DatabaseConnection, player_id: int, amount: int) -> int:
    cursor = db.get_cursor()
    try:
        cursor.execute("UPDATE player SET balance = balance + %s WHERE player_id = %s", (amount, player_id))
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (player_id,))
        return cursor.fetchone()['balance']
    finally:
        cursor.close()

def record_transaction(db: DatabaseConnection, game_id: int, from_player: Optional[int], to_player: Optional[int], amount: int, transaction_type: str):
    cursor = db.get_cursor()
    try:
        if amount <= 0: return
        if from_player is not None:
            cursor.execute("INSERT INTO transaction (amount, transaction_type, transaction_time, player_id, game_id) VALUES (%s, %s, NOW(), %s, %s)", (amount, transaction_type, from_player, game_id))
            update_player_balance(db, from_player, -amount)
        if to_player is not None:
            cursor.execute("INSERT INTO transaction (amount, transaction_type, transaction_time, player_id, game_id) VALUES (%s, %s, NOW(), %s, %s)", (amount, transaction_type, to_player, game_id))
            update_player_balance(db, to_player, amount)
    finally:
        cursor.close()

def record_game_event(db: DatabaseConnection, game_id: int, event_type: str, description: str):
    cursor = db.get_cursor()
    try:
        cursor.execute("INSERT INTO log (eventType, eventDescription, event_time, game_id) VALUES (%s, %s, NOW(), %s)", (event_type, description, game_id))
    finally:
        cursor.close()

def roll_dice() -> Tuple[int, int, bool]:
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    return d1, d2, d1 == d2

def handle_pass_go(db: DatabaseConnection, game_id: int, player_id: int, amount: int):
    record_transaction(db, game_id, None, player_id, amount, "salary")
    record_game_event(db, game_id, "system", f"Player {player_id} collected ${amount} at GO.")

def detect_space_type(db: DatabaseConnection, position: int) -> dict:
    cursor = db.get_cursor()
    try:
        # Joining the property table so we can safely get propSet without crashing on non-properties
        cursor.execute("""
            SELECT b.space_id, b.type, b.name, p.propSet 
            FROM boardspace b 
            LEFT JOIN property p ON b.space_id = p.space_id 
            WHERE b.index_no = %s
        """, (position,))
        return cursor.fetchone() or {}
    finally:
        cursor.close()

def handle_property_space(db: DatabaseConnection, game_id: int, active_player_id: int, space_id: int, prop_name: str):
    cursor = db.get_cursor()
    try:
        # 1. We first need to get the actual property_id for this space!
        cursor.execute("SELECT property_id, cost, rent, isMortgaged FROM property WHERE space_id = %s", (space_id,))
        prop_data = cursor.fetchone()
        
        if not prop_data:
            print(f"⚠️ DATABASE ERROR: '{prop_name}' (Space {space_id}) is missing its financial data! Contact Admin.")
            return
            
        actual_prop_id = prop_data['property_id']
        cost = prop_data['cost']
        
        # 2. Check ownership using the CORRECT actual_prop_id
        cursor.execute("SELECT player_id AS owner_id FROM ownership WHERE property_id = %s AND end_time IS NULL", (actual_prop_id,))
        ownership = cursor.fetchone()
        
        if not ownership:
            print(f"\n{prop_name} is unowned. Cost: ${cost}")
            choice = input("Would you like to buy it? (y/n): ")
            if choice.lower() == 'y':
                cursor.execute("SELECT balance FROM player WHERE player_id = %s", (active_player_id,))
                if cursor.fetchone()['balance'] >= cost:
                    record_transaction(db, game_id, active_player_id, None, cost, "purchase")
                    
                    # NOTE: Ensure your stored procedure 'sp_transfer_property' expects the property_id, not space_id!
                    cursor.callproc('sp_transfer_property', [actual_prop_id, active_player_id])
                    db.commit()
                    
                    print(f"Successfully purchased {prop_name}!")
                    record_game_event(db, game_id, "transaction", f"Player {active_player_id} bought {prop_name} for ${cost}")
                else:
                    print("Insufficient funds.")
                    
        elif ownership['owner_id'] != active_player_id:
            if not prop_data['isMortgaged']:
                print(f"Owned by Player {ownership['owner_id']}. You pay ${prop_data['rent']} in rent.")
                record_transaction(db, game_id, active_player_id, ownership['owner_id'], prop_data['rent'], "rent")
                record_game_event(db, game_id, "rent", f"Player {active_player_id} paid ${prop_data['rent']} rent to Player {ownership['owner_id']}")
            else:
                print(f"{prop_name} is mortgaged. No rent due.")
    finally:
        cursor.close()

def handle_card_space(db: DatabaseConnection, game_id: int, player_id: int, card_type: str):
    cursor = db.get_cursor()
    try:
        # Pick a random card of that type
        cursor.execute("SELECT * FROM chance_chest_cards WHERE type = %s ORDER BY RAND() LIMIT 1", (card_type,))
        card = cursor.fetchone()
        
        if not card:
            print(f"No {card_type} cards found in database!")
            return

        print(f"\n🎴 {card_type.upper()} CARD: {card['description']}")
        
        # --- Standard Money Card ---
        if card['action_type'] == 'money':
            amount = card['value']
            trans_type = "tax" if amount < 0 else "salary"
            record_transaction(db, game_id, None, player_id, abs(amount), trans_type)
            
        # --- NEW: Multi-Player Money Card (Grand Opera Night / Birthday) ---
        elif card['action_type'] == 'multi_money':
            amount_per_player = card['value']
            
            # 1. Get all other players in this game who aren't bankrupt
            cursor.execute("""
                SELECT player_id, name FROM player 
                WHERE game_id = %s AND player_id != %s AND isEliminated = FALSE
            """, (game_id, player_id))
            others = cursor.fetchall()
            
            for other in others:
                if amount_per_player > 0:
                    # Current player COLLECTS from others (e.g., Birthday)
                    # Other pays Current Player
                    record_transaction(db, game_id, other['player_id'], player_id, amount_per_player, "rent")
                    print(f"Collected ${amount_per_player} from {other['name']}")
                else:
                    # Current player PAYS others (e.g., Chairman of the Board)
                    # Current player pays Other
                    pay_amt = abs(amount_per_player)
                    record_transaction(db, game_id, player_id, other['player_id'], pay_amt, "tax")
                    print(f"Paid ${pay_amt} to {other['name']}")

        # --- Jail Card ---
        elif card['action_type'] == 'jail':
            cursor.execute("SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = 10", (game_id,))
            jail_space = cursor.fetchone()
            if jail_space:
                cursor.execute("UPDATE player SET position = %s, inJail = TRUE, jailTurns = 0 WHERE player_id = %s", 
                               (jail_space['space_id'], player_id))
                print("👮 You were sent to Jail (Index 10)!")

        # --- Move Card ---
        elif card['action_type'] == 'move':
            target_idx = card['value']
            cursor.execute("SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = %s", (game_id, target_idx))
            new_space = cursor.fetchone()
            if new_space:
                # Note: This is a simple teleport. If you want them to collect GO 
                # when passing, you'd need to call the movement logic from interactive_turn.
                cursor.execute("UPDATE player SET position = %s WHERE player_id = %s", (new_space['space_id'], player_id))
                print(f"🚀 Moved to index {target_idx}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error resolving card: {e}")
    finally:
        cursor.close()
        
# --- ADMIN FUNCTIONS ---
def admin_eliminate_player(db: DatabaseConnection, game_id: int, target_player_id: int):
    """Admin tool to remove a player and seize their assets without breaking history."""
    cursor = db.get_cursor()
    try:
        # 1. Bankrupt and eliminate the player
        cursor.execute("""
            UPDATE player 
            SET isBankrupt = TRUE, isEliminated = TRUE, balance = 0 
            WHERE player_id = %s
        """, (target_player_id,))
        
        # 2. Confiscate all active properties (Return them to the bank by setting end_time)
        cursor.execute("""
            UPDATE ownership 
            SET end_time = NOW() 
            WHERE player_id = %s AND end_time IS NULL
        """, (target_player_id,))
        
        # 3. Log the Admin action
        record_game_event(db, game_id, "system", f"Admin eliminated Player {target_player_id} and seized their assets.")
        db.commit()
        print(f"✅ Admin: Player {target_player_id} has been eliminated and properties returned to the bank.")
        
    except Exception as e:
        db.rollback()
        print(f"🚨 Admin action failed: {e}")
    finally:
        cursor.close()

def admin_add_property(db: DatabaseConnection, game_id: int, index_no: int, name: str, prop_set: str, cost: int, rent: int):
    """Admin tool to build or overwrite a property space on a SPECIFIC game board."""
    cursor = db.get_cursor()
    try:
        # Standard Monopoly scaling multipliers
        rent_1 = rent * 5
        rent_2 = rent * 15
        rent_3 = rent * 45
        rent_4 = rent * 80
        rent_h = rent * 100
        
        cursor.execute("SELECT space_id FROM boardspace WHERE index_no = %s AND game_id = %s", (index_no, game_id))
        existing = cursor.fetchone()
        
        if existing:
            space_id = existing['space_id']
            cursor.execute("UPDATE boardspace SET type = 'property', name = %s WHERE space_id = %s", (name, space_id))
            
            cursor.execute("SELECT property_id FROM property WHERE property_id = %s", (space_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE property 
                    SET propSet = %s, cost = %s, rent = %s, rent_1 = %s, rent_2 = %s, rent_3 = %s, rent_4 = %s, rent_h = %s, name = %s, isMortgaged = FALSE, houses = 0 
                    WHERE property_id = %s
                """, (prop_set, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, name, space_id))
            else:
                cursor.execute("""
                    INSERT INTO property (property_id, propSet, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, isMortgaged, houses, name, space_id, houseCost) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, 0, %s, %s, 50)
                """, (space_id, prop_set, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, name, space_id))
        else:
            cursor.execute("SELECT COALESCE(MAX(space_id), 0) + 1 as next_id FROM boardspace")
            space_id = cursor.fetchone()['next_id']
            
            cursor.execute("""
                INSERT INTO boardspace (space_id, index_no, type, name, game_id) 
                VALUES (%s, %s, 'property', %s, %s)
            """, (space_id, index_no, name, game_id))
            
            cursor.execute("""
                INSERT INTO property (property_id, propSet, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, isMortgaged, houses, name, space_id, houseCost) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, 0, %s, %s, 50)
            """, (space_id, prop_set, cost, rent, rent_1, rent_2, rent_3, rent_4, rent_h, name, space_id))
        
        db.commit()
        print(f"✅ Admin: Built '{name}' at index {index_no} for Game {game_id}.")
        
    except Exception as e:
        db.rollback()
        print(f"🚨 Admin action failed: {e}")
    finally:
        cursor.close()

def admin_add_special_space(db: DatabaseConnection, game_id: int):
    """Option 6: Build non-property spaces like Tax, Chance, etc."""
    cursor = db.get_cursor()
    try:
        idx = int(input("Enter Board Index (0-39): "))
        if idx < 0 or idx > 39:
            print("Invalid index. Must be 0-39.")
            return

        # Check for existing space
        cursor.execute("SELECT name, type FROM boardspace WHERE game_id = %s AND index_no = %s", (game_id, idx))
        existing = cursor.fetchone()
        if existing:
            confirm = input(f"Index {idx} is currently '{existing['name']}' ({existing['type']}). Overwrite? (y/n): ")
            if confirm.lower() != 'y':
                print("Action aborted.")
                return

        print("\nSelect Space Type:")
        print("[1] Tax\n[2] Chance\n[3] Chest\n[4] Jail (Go to Jail)\n[5] Free Parking")
        stype_choice = input("Choice: ")
        
        mapping = {'1':'tax', '2':'chance', '3':'chest', '4':'jail', '5':'free'}
        if stype_choice not in mapping:
            print("Invalid choice.")
            return
            
        stype = mapping[stype_choice]
        name = input("Enter display name for this space (e.g., 'Income Tax'): ")
        
        # If tax, we need an amount. We'll reuse the 'rent' column in property 
        # or simply store it in the name/metadata. Better yet, let's assume 
        # taxes are fixed or asked here.
        tax_amount = 0
        if stype == 'tax':
            tax_amount = int(input("Enter Tax Amount: "))
            name = f"{name} (${tax_amount})" # We'll embed the amount in the name for now

        # Create/Update boardspace
        if existing:
            cursor.execute("UPDATE boardspace SET type = %s, name = %s WHERE game_id = %s AND index_no = %s",
                           (stype, name, game_id, idx))
        else:
            cursor.execute("SELECT COALESCE(MAX(space_id), 0) + 1 as next_id FROM boardspace")
            s_id = cursor.fetchone()['next_id']
            cursor.execute("INSERT INTO boardspace (space_id, index_no, type, name, game_id) VALUES (%s, %s, %s, %s, %s)",
                           (s_id, idx, stype, name, game_id))
        
        db.commit()
        print(f"✅ Successfully added {stype} space at index {idx}.")
    except Exception as e:
        db.rollback()
        print(f"🚨 Admin action failed: {e}")
    finally:
        cursor.close()

def admin_remove_property(db: DatabaseConnection, game_id: int, space_id: int):
    """Admin tool to demolish a property so it can no longer be bought or trigger rent."""
    cursor = db.get_cursor()
    try:
        # 1. Forcefully evict the current owner (if any)
        cursor.execute("UPDATE ownership SET end_time = NOW() WHERE property_id = %s AND end_time IS NULL", (space_id,))
        
        # 2. Change the space type so it's ignored by the game loop, and update the name
        cursor.execute("""
            UPDATE boardspace 
            SET type = 'blank', name = CONCAT(name, ' [DEMOLISHED]') 
            WHERE space_id = %s
        """, (space_id,))
        
        record_game_event(db, game_id, "system", f"Admin demolished property at space_id {space_id}.")
        db.commit()
        print(f"✅ Admin: Property {space_id} has been demolished and is now a blank space.")
        
    except Exception as e:
        db.rollback()
        print(f"🚨 Admin action failed: {e}")
    finally:
        cursor.close()
# --- INTERACTIVE CLI MENUS ---

def view_player_stats(db: DatabaseConnection, player_id: int, player_name: str):
    cursor = db.get_cursor()
    try:
        cursor.execute("""
            SELECT p.balance, b.index_no 
            FROM player p
            JOIN boardspace b ON p.position = b.space_id
            WHERE p.player_id = %s
        """, (player_id,))
        p = cursor.fetchone()
        
        cursor.execute("""
            SELECT p.name, p.isMortgaged 
            FROM property p 
            JOIN ownership o ON p.property_id = o.property_id 
            WHERE o.player_id = %s AND o.end_time IS NULL
        """, (player_id,))
        properties = cursor.fetchall()
        
        # Display the stats
        print(f"\n--- {player_name}'s Status ---")
        print(f"Balance: ${p['balance']}")
        print(f"Position (Index): {p['index_no']}")
        print("Properties Owned:")
        if not properties:
            print("  (None)")
        for prop in properties:
            status = "(Mortgaged)" if prop['isMortgaged'] else ""
            print(f"  - {prop['name']} {status}")
            
    finally:
        cursor.close()

def manage_properties_menu(db: DatabaseConnection, game_id: int, player_id: int):
    cursor = db.get_cursor()
    try:
        # 1. Fixed the JOIN to get the correct name from boardspace
        # Also grabbing 'houses' to show the player
        cursor.execute("""
            SELECT p.property_id, p.name, p.cost, p.isMortgaged, p.houses 
            FROM property p 
            JOIN ownership o ON p.property_id = o.property_id 
            JOIN boardspace b ON p.property_id = b.space_id
            WHERE o.player_id = %s AND o.end_time IS NULL
        """, (player_id,))
        props = cursor.fetchall()
    finally:
        cursor.close()

    if not props:
        print("You don't own any properties.")
        return

    print("\n--- Manage Properties ---")
    for idx, prop in enumerate(props):
        status = "MORTGAGED" if prop['isMortgaged'] else "ACTIVE"
        house_str = f" ({prop['houses']} Houses)" if prop['houses'] > 0 else ""
        print(f"[{idx+1}] {prop['name']}{house_str} ({status}) - Base Value: ${prop['cost']}")
    
    print("[0] Cancel")
    
    # 2. Moved the input inside a try block to prevent crashes!
    try:
        choice = int(input("Select a property to toggle mortgage (or 0 to exit): "))
        if choice == 0 or choice > len(props) or choice < 0: 
            return

        selected = props[choice-1]
        prop_id = selected['property_id']
        prop_name = selected['name']
        
        # Open a new cursor for the database updates
        cursor = db.get_cursor()
        
        if selected['isMortgaged']:
            cost = int((selected['cost'] // 2) * 1.10)
            ans = input(f"Unmortgage {prop_name} for ${cost}? (y/n): ")
            if ans.lower() == 'y':
                cursor.execute("SELECT balance FROM player WHERE player_id = %s", (player_id,))
                if cursor.fetchone()['balance'] >= cost:
                    # Deduct money and update property state
                    record_transaction(db, game_id, player_id, None, cost, "unmortgage")
                    cursor.execute("UPDATE property SET isMortgaged = FALSE WHERE property_id = %s", (prop_id,))
                    db.commit()
                    record_game_event(db, game_id, "transaction", f"Player {player_id} unmortgaged {prop_name}")
                    print(f"Successfully unmortgaged {prop_name}!")
                else:
                    print("Insufficient funds to unmortgage.")
        else:
            gain = selected['cost'] // 2
            ans = input(f"Mortgage {prop_name} for ${gain}? (y/n): ")
            if ans.lower() == 'y':
                # Update property state and give money
                cursor.execute("UPDATE property SET isMortgaged = TRUE WHERE property_id = %s", (prop_id,))
                db.commit()
                record_transaction(db, game_id, None, player_id, gain, "mortgage")
                record_game_event(db, game_id, "transaction", f"Player {player_id} mortgaged {prop_name}")
                print(f"Successfully mortgaged {prop_name}!")
                
    except ValueError:
        print("Invalid input. Please enter a valid number.")
    except Exception as e:
        # 3. This catches our SQL Rule Violation Trigger if they try to mortgage a property with houses!
        db.rollback() 
        print(f"\nAction failed: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()

def handle_trades_menu(db: DatabaseConnection, game_id: int, player_id: int):
    print("\n--- Trade Menu ---")
    print("[1] View Pending Incoming Trades")
    print("[2] Initiate New Trade")
    print("[0] Back")
    
    choice = input("> ")
    if choice == '1':
            view_incoming_trades(db, game_id, player_id)
    elif choice == '2':
        initiate_trade(db, game_id, player_id)
    elif choice == '0': return
    else:
            print("Invalid choice.")

def initiate_trade(db: DatabaseConnection, game_id: int, player_id: int):
    cursor = db.get_cursor()
    try:
        # 1. Fetch and Display Your Assets
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (player_id,))
        my_balance = cursor.fetchone()['balance']
        
        cursor.execute("""
            SELECT p.property_id, p.name, p.propSet, p.cost 
            FROM property p 
            JOIN ownership o ON p.property_id = o.property_id 
            WHERE o.player_id = %s AND o.end_time IS NULL
        """, (player_id,))
        my_props = cursor.fetchall()
        
        print("\n" + "="*45)
        print(f" YOUR ASSETS (Net Balance: ${my_balance})")
        print("="*45)
        if my_props:
            for p in my_props:
                print(f"  [ID: {p['property_id']}] {p['name']} ({p['propSet']}) - Value: ${p['cost']}")
        else:
            print("  No properties owned.")
            
        # 2. Select Target Player
        cursor.execute("SELECT player_id, name FROM player WHERE game_id = %s AND isEliminated = FALSE AND player_id != %s", (game_id, player_id))
        targets = cursor.fetchall()
        
        if not targets:
            print("\nNo other active players available to trade with.")
            return
            
        print("\nSelect target player:")
        for idx, t in enumerate(targets):
            print(f"[{idx+1}] {t['name']} (ID: {t['player_id']})")
            
        t_choice = int(input("Choice: ")) - 1
        if t_choice < 0 or t_choice >= len(targets):
            print("Invalid choice.")
            return
            
        receiver_id = targets[t_choice]['player_id']
        receiver_name = targets[t_choice]['name']
        
        # 3. Fetch and Display Their Assets
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (receiver_id,))
        their_balance = cursor.fetchone()['balance']
        
        cursor.execute("""
            SELECT p.property_id, p.name, p.propSet, p.cost 
            FROM property p 
            JOIN ownership o ON p.property_id = o.property_id 
            WHERE o.player_id = %s AND o.end_time IS NULL
        """, (receiver_id,))
        their_props = cursor.fetchall()
        
        print("\n" + "="*45)
        print(f" {receiver_name.upper()}'S ASSETS (Net Balance: ${their_balance})")
        print("="*45)
        if their_props:
            for p in their_props:
                print(f"  [ID: {p['property_id']}] {p['name']} ({p['propSet']}) - Value: ${p['cost']}")
        else:
            print("  No properties owned.")
            
        # 4. Negotiate Cash
        print("\n--- Trade Terms ---")
        offered_cash = int(input(f"Amount of cash to OFFER them (0 for none): $"))
        requested_cash = int(input(f"Amount of cash to REQUEST from them (0 for none): $"))
        
        # 5. Select Properties
        offer_prop_ids = []
        if my_props:
            offer_str = input("\nEnter Property IDs to OFFER (comma-separated, or leave blank): ")
            if offer_str.strip():
                offer_prop_ids = [int(x.strip()) for x in offer_str.split(',')]
                
        req_prop_ids = []
        if their_props:
            req_str = input("Enter Property IDs to REQUEST (comma-separated, or leave blank): ")
            if req_str.strip():
                req_prop_ids = [int(x.strip()) for x in req_str.split(',')]
        
        # 6. Build the Trade in the Database
        cursor.execute("SELECT COALESCE(MAX(trade_id), 0) + 1 as next_id FROM trade")
        trade_id = cursor.fetchone()['next_id']
        
        cursor.execute("""
            INSERT INTO trade (trade_id, status, offeredCash, requestedCash, negotiationRound, proposer_id, receiver_id, game_id)
            VALUES (%s, 'pending', %s, %s, 0, %s, %s, %s)
        """, (trade_id, offered_cash, requested_cash, player_id, receiver_id, game_id))
        
        for pid in offer_prop_ids:
            cursor.execute("INSERT INTO trade_offers (trade_id, property_id) VALUES (%s, %s)", (trade_id, pid))
            
        for pid in req_prop_ids:
            cursor.execute("INSERT INTO trade_requests (trade_id, property_id) VALUES (%s, %s)", (trade_id, pid))
            
        db.commit()
        print(f"✅ Trade Proposal sent to {receiver_name}!")
        
    except ValueError:
        print("Invalid number entered. Trade aborted.")
    except Exception as e:
        db.rollback()
        print(f"Trade Creation Error: {e}")
    finally:
        cursor.close()

def view_incoming_trades(db: DatabaseConnection, game_id: int, player_id: int):
    cursor = db.get_cursor()
    try:
        cursor.execute("""
            SELECT t.trade_id, t.proposer_id, p.name as proposer_name, t.offeredCash, t.requestedCash
            FROM trade t
            JOIN player p ON t.proposer_id = p.player_id
            WHERE t.receiver_id = %s AND t.status = 'pending' AND t.game_id = %s
        """, (player_id, game_id))
        trades = cursor.fetchall()
        
        if not trades:
            print("\nYou have no pending incoming trades.")
            return
            
        for t in trades:
            tid = t['trade_id']
            print(f"\n{'='*30}")
            print(f" INCOMING TRADE #{tid} FROM {t['proposer_name'].upper()}")
            print(f"{'='*30}")
            print(f"They offer cash: ${t['offeredCash']}")
            
            # Show offered properties
            cursor.execute("SELECT p.name FROM property p JOIN trade_offers tro ON p.property_id = tro.property_id WHERE tro.trade_id = %s", (tid,))
            offers = cursor.fetchall()
            if offers:
                print("They offer properties: " + ", ".join([o['name'] for o in offers]))
                
            print(f"\nThey request cash: ${t['requestedCash']}")
            
            # Show requested properties
            cursor.execute("SELECT p.name FROM property p JOIN trade_requests trr ON p.property_id = trr.property_id WHERE trr.trade_id = %s", (tid,))
            reqs = cursor.fetchall()
            if reqs:
                print("They request properties: " + ", ".join([r['name'] for r in reqs]))
                
            choice = input(f"\nAccept trade #{tid}? (y/n/ignore): ").lower()
            if choice == 'y':
                process_trade_acceptance(db, game_id, tid, t['proposer_id'], player_id, t['offeredCash'], t['requestedCash'])
            elif choice == 'n':
                cursor.execute("UPDATE trade SET status = 'declined' WHERE trade_id = %s", (tid,))
                db.commit()
                print(f"Trade #{tid} declined.")
                
    except Exception as e:
        print(f"Error fetching trades: {e}")
    finally:
        cursor.close()

def process_trade_acceptance(db: DatabaseConnection, game_id: int, trade_id: int, proposer_id: int, receiver_id: int, offered_cash: int, requested_cash: int):
    cursor = db.get_cursor()
    try:
        # 1. Verify balances before doing anything
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (proposer_id,))
        if cursor.fetchone()['balance'] < offered_cash:
            print("🚨 Trade failed: The proposer spent their cash and can no longer afford this trade!")
            return
            
        cursor.execute("SELECT balance FROM player WHERE player_id = %s", (receiver_id,))
        if cursor.fetchone()['balance'] < requested_cash:
            print("🚨 Trade failed: You do not have enough cash to fulfill this trade!")
            return
            
        # 2. Transfer Cash (Changed "trade" to "purchase")
        if offered_cash > 0:
            record_transaction(db, game_id, proposer_id, receiver_id, offered_cash, "purchase")
        if requested_cash > 0:
            record_transaction(db, game_id, receiver_id, proposer_id, requested_cash, "purchase")
            
        # 3. Transfer Properties Offered (To Receiver)
        cursor.execute("SELECT property_id FROM trade_offers WHERE trade_id = %s", (trade_id,))
        for row in cursor.fetchall():
            cursor.callproc('sp_transfer_property', [row['property_id'], receiver_id])
            
        # 4. Transfer Properties Requested (To Proposer)
        cursor.execute("SELECT property_id FROM trade_requests WHERE trade_id = %s", (trade_id,))
        for row in cursor.fetchall():
            cursor.callproc('sp_transfer_property', [row['property_id'], proposer_id])
            
        # 5. Mark Trade as Accepted & Log it
        cursor.execute("UPDATE trade SET status = 'accepted' WHERE trade_id = %s", (trade_id,))
        record_game_event(db, game_id, "trade", f"Trade #{trade_id} accepted between Player {proposer_id} and Player {receiver_id}.")
        
        db.commit()
        print(f"✅ Trade #{trade_id} successfully executed!")
        
    except Exception as e:
        db.rollback()
        print(f"🚨 Critical error processing trade. Rolled back to protect game state: {e}")
    finally:
        cursor.close()

def interactive_turn(db: DatabaseConnection, game_id: int, player: dict) -> bool:
    """Handles a full player turn. Returns False if player is eliminated."""
    player_id = player['player_id']
    player_name = player['name']
    
    # --- 1. INITIALIZE THE TURN ---
    cursor = db.get_cursor()
    try:
        cursor.execute("SELECT position FROM player WHERE player_id = %s", (player_id,))
        current_pos_id = cursor.fetchone()['position']
        
        cursor.execute("SELECT COALESCE(MAX(turn_id), 0) + 1 as next_id FROM turn")
        turn_id = cursor.fetchone()['next_id']
        
        cursor.execute("""
            INSERT INTO turn (turn_id, prev_position, player_id, game_id, is_completed)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (turn_id, current_pos_id, player_id, game_id))
        db.commit()
    finally:
        cursor.close()

    has_rolled = False
    turn_active = True
    
    print(f"\n=====================================")
    print(f"       {player_name}'S TURN (Game #{game_id})")
    print(f"=====================================")
    
    while turn_active:
        print("\nActions:")
        print("[1] Roll Dice" if not has_rolled else "[1] Roll Dice (Already Rolled)")
        print("[2] Manage Properties")
        print("[3] Trading")
        print("[4] View My Stats")
        print("[5] End Turn")
        
        choice = input(f"{player_name}, choose an action: ")
        
        if choice == '1':
            if has_rolled:
                print("Already rolled!")
            else:
                cursor = db.get_cursor()
                try:
                    # Check Jail/Balance
                    cursor.execute("SELECT inJail, balance FROM player WHERE player_id = %s", (player_id,))
                    p_state = cursor.fetchone()
                    
                    if p_state['inJail']:
                        print("🚨 You are in JAIL!")
                        if p_state['balance'] >= 50:
                            if input("Pay $50 bail? (y/n): ").lower() == 'y':
                                record_transaction(db, game_id, player_id, None, 50, "fine")
                                cursor.execute("UPDATE player SET inJail = FALSE, jailTurns = 0 WHERE player_id = %s", (player_id,))
                                db.commit()
                                print("You are free!")

                    d1, d2, is_double = roll_dice()
                    total_moved = d1 + d2
                    print(f"\n🎲 Rolled: {d1}, {d2} (Total: {total_moved})")

                    # --- DYNAMIC MOVEMENT & CROSSING GO ---
                    cursor.execute("""
                        SELECT b.index_no, 
                               (SELECT COALESCE(MAX(index_no), 0) FROM boardspace WHERE game_id = %s) as max_idx 
                        FROM boardspace b 
                        WHERE b.space_id = %s AND b.game_id = %s
                    """, (game_id, current_pos_id, game_id))
                    pos_data = cursor.fetchone()
                    
                    current_idx = pos_data['index_no'] if pos_data else 0
                    max_idx = pos_data['max_idx'] if pos_data else 0
                    board_size = max_idx + 1
                    
                    new_index = (current_idx + total_moved) % board_size
                    crossings = (current_idx + total_moved) // board_size

                    cursor.execute("SELECT space_id, name, type FROM boardspace WHERE game_id = %s AND index_no = %s", (game_id, new_index))
                    target_row = cursor.fetchone()
                    
                    if not target_row:
                        print(f"❌ Error: Index {new_index} missing!")
                        continue
                    
                    intended_pos_id = target_row['space_id']
                    
                    # Check for movement blocks (Triggers)
                    cursor.execute("UPDATE turn SET dice1 = %s, dice2 = %s, new_position = %s WHERE turn_id = %s", 
                                 (d1, d2, intended_pos_id, turn_id))
                    db.commit()
                    
                    cursor.execute("SELECT new_position FROM turn WHERE turn_id = %s", (turn_id,))
                    actual_pos_id = cursor.fetchone()['new_position']
                    
                    # --- NEW JAIL & MOVEMENT VALIDATION ---
                    cursor.execute("SELECT inJail, jailTurns FROM player WHERE player_id = %s", (player_id,))
                    jail_status = cursor.fetchone()

                    if jail_status['inJail'] and total_moved > 0:
                        # Movement is actually blocked by the database trigger because player is in Jail
                        current_turn = jail_status['jailTurns'] + 1
                        print(f"🔒 Movement blocked. You are in Jail (Turn {current_turn}/3).")
                        cursor.execute("UPDATE player SET jailTurns = %s WHERE player_id = %s", (current_turn, player_id))
                        
                        if current_turn >= 3:
                            print("🔓 You have served your sentence. You will be released next turn.")
                            cursor.execute("UPDATE player SET inJail = FALSE, jailTurns = 0 WHERE player_id = %s", (player_id,))
                        db.commit()
                    else:
                        # Normal movement (or we landed back on the same spot on a tiny board)
                        cursor.execute("UPDATE player SET position = %s WHERE player_id = %s", (actual_pos_id, player_id))
                        db.commit()

                        # --- GO RESOLUTION (Keep your existing crossing logic) ---
                        if crossings > 0:
                            go_amount = (300 if new_index == 0 else 0) + (200 * (crossings - 1 if new_index == 0 else crossings))
                            if go_amount > 0:
                                handle_pass_go(db, game_id, player_id, go_amount)
                                print(f"💰 Collected ${go_amount} from GO!")

                        print(f"Landed on Index {new_index}: {target_row['name']} ({target_row['type']})")

                        # --- SPACE RESOLUTION ---
                        s_type = target_row['type']
                        if s_type == 'property':
                            handle_property_space(db, game_id, player_id, actual_pos_id, target_row['name'])
                        
                        elif s_type in ['chance', 'chest']:
                            handle_card_space(db, game_id, player_id, s_type)
                        
                        elif s_type == 'tax':
                            import re
                            match = re.search(r'\$(\d+)', target_row['name'])
                            tax_val = int(match.group(1)) if match else 100
                            print(f"💸 Tax due: ${tax_val}")
                            record_transaction(db, game_id, player_id, None, tax_val, "tax")
                        
                        elif s_type == 'jail':
                            # Landed on a "Go to Jail" space
                            cursor.execute("SELECT space_id FROM boardspace WHERE game_id = %s AND index_no = 10", (game_id,))
                            jail_target = cursor.fetchone()
                            if jail_target:
                                cursor.execute("UPDATE player SET position = %s, inJail = TRUE, jailTurns = 0 WHERE player_id = %s", 
                                               (jail_target['space_id'], player_id))
                                db.commit()
                                print("👮 Go to Jail! Move directly to Index 10. Do not pass GO.")

                finally:
                    cursor.close()
                has_rolled = True

        elif choice == '2':
            manage_properties_menu(db, game_id, player_id)
        elif choice == '3':
            handle_trades_menu(db, game_id, player_id)
        elif choice == '4':
            view_player_stats(db, player_id, player_name)
        elif choice == '5':
            if not has_rolled:
                print("Roll first!")
            else:
                cursor = db.get_cursor()
                try:
                    cursor.execute("UPDATE turn SET is_completed = TRUE WHERE turn_id = %s", (turn_id,))
                    db.commit()
                    cursor.execute("SELECT isEliminated FROM player WHERE player_id = %s", (player_id,))
                    if cursor.fetchone().get('isEliminated'):
                        print(f"💀 {player_name} is Bankrupt!")
                        return False
                    turn_active = False 
                finally:
                    cursor.close()
    return True

def reset_game_state(db: DatabaseConnection, game_id: int):
    """
    Resets all data for a specific game ID to starting conditions.
    Deletes records in a specific order to avoid Foreign Key Constraint violations.
    """
    cursor = db.get_cursor()
    try:
        print(f"--- Resetting Game {game_id} ---")
        
        # 1. Clear Trade Details first (The "children" causing the constraint error)
        # These must be deleted before the main 'trade' table records
        cursor.execute("""
            DELETE FROM trade_offers 
            WHERE trade_id IN (SELECT trade_id FROM trade WHERE game_id = %s)
        """, (game_id,))
        
        cursor.execute("""
            DELETE FROM trade_requests 
            WHERE trade_id IN (SELECT trade_id FROM trade WHERE game_id = %s)
        """, (game_id,))

        # 2. Clear main Trade records
        cursor.execute("DELETE FROM trade WHERE game_id = %s", (game_id,))

        # 3. Clear Ownership records for all players in this game
        cursor.execute("""
            DELETE FROM ownership 
            WHERE player_id IN (SELECT player_id FROM player WHERE game_id = %s)
        """, (game_id,))

        # 4. Wipe Game History (Logs, Turns, and Transactions)
        cursor.execute("DELETE FROM log WHERE game_id = %s", (game_id,))
        cursor.execute("DELETE FROM turn WHERE game_id = %s", (game_id,))
        cursor.execute("DELETE FROM transaction WHERE game_id = %s", (game_id,))

        # 5. Reset Properties associated with this game's board
        # (This resets house counts and mortgage status)
        cursor.execute("""
            UPDATE property 
            SET houses = 0, isMortgaged = 0 
            WHERE space_id IN (SELECT space_id FROM boardspace)
        """)

        # 6. Reset Player Stats to starting values
        cursor.execute("""
            UPDATE player 
            SET balance = 1500, 
                position = 0, 
                inJail = 0, 
                jailTurns = 0, 
                isBankrupt = 0, 
                isEliminated = 0 
            WHERE game_id = %s
        """, (game_id,))

        # 7. Reset Game Status
        cursor.execute("UPDATE game SET status = 'running' WHERE game_id = %s", (game_id,))

        db.commit()
        print(f"✅ Successfully reset Game {game_id} to default settings.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Reset Failed: {e}")
    finally:
        cursor.close()

def end_game_session(db: DatabaseConnection, game_id: int):
    """Option 8: Updates status to 'finished'. Python logic should check this before turns."""
    cursor = db.get_cursor()
    try:
        cursor.execute("UPDATE game SET status = 'finished' WHERE game_id = %s", (game_id,))
        db.commit()
        print(f"✅ Game {game_id} has been officially ended.")
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to end game: {e}")
    finally:
        cursor.close()

def delete_game_completely(db: DatabaseConnection, game_id: int):
    """Option 9: The 'Nuclear' option. Wipes everything including the game entry itself."""
    cursor = db.get_cursor()
    try:
        print(f"--- Purging All Data for Game {game_id} ---")
        
        # 1. Child Trade tables
        cursor.execute("DELETE FROM trade_offers WHERE trade_id IN (SELECT trade_id FROM trade WHERE game_id = %s)", (game_id,))
        cursor.execute("DELETE FROM trade_requests WHERE trade_id IN (SELECT trade_id FROM trade WHERE game_id = %s)", (game_id,))
        
        # 2. Parent Trade table
        cursor.execute("DELETE FROM trade WHERE game_id = %s", (game_id,))
        
        # 3. Logs and History
        cursor.execute("DELETE FROM log WHERE game_id = %s", (game_id,))
        cursor.execute("DELETE FROM turn WHERE game_id = %s", (game_id,))
        cursor.execute("DELETE FROM transaction WHERE game_id = %s", (game_id,))
        
        # 4. Ownership (Players must exist for this, so do it before deleting players)
        cursor.execute("DELETE FROM ownership WHERE player_id IN (SELECT player_id FROM player WHERE game_id = %s)", (game_id,))
        
        # 5. Players
        cursor.execute("DELETE FROM player WHERE game_id = %s", (game_id,))

        # --- FIX STARTS HERE ---
        # 6. Delete Properties (The "children" of boardspaces)
        cursor.execute("""
            DELETE FROM property 
            WHERE space_id IN (SELECT space_id FROM boardspace WHERE game_id = %s)
        """, (game_id,))
        
        # 7. Delete BoardSpaces (The "parents" of properties)
        cursor.execute("DELETE FROM boardspace WHERE game_id = %s", (game_id,))
        # --- FIX ENDS HERE ---
        
        # 8. Finally, the Game record itself
        cursor.execute("DELETE FROM game WHERE game_id = %s", (game_id,))
        
        db.commit()
        print(f"💥 Game {game_id} and all associated data have been deleted.")
    except Exception as e:
        db.rollback()
        print(f"❌ Delete Failed: {e}")
    finally:
        cursor.close()

def start_interactive_session():
    db = DatabaseConnection()
    try:
        print("\n" + "="*40)
        print("   MONOPOLY REAL ESTATE SIMULATOR")
        print("="*40)
        
        # --- NEW MENU ---
        print("[1] Start a New Simulation (New Game ID)")
        print("[2] Resume an Existing Simulation")
        start_choice = input("Choice: ")
        
        if start_choice == '2':
            game_id = int(input("Enter existing Game ID to resume (e.g., 1): "))
            print(f"Resuming Game Session #{game_id}...")
            # We skip initial setup because players are already registered!
        else:
            game_id = start_game(db)
            print(f"Started Game Session #{game_id}")
            # --- 1. INITIAL PLAYER SETUP ---
            try:
                num_players = int(input("\nEnter initial number of players (e.g., 2-6): "))
            except ValueError:
                num_players = 0
                print("Invalid input. Starting with 0 players.")

            for i in range(num_players):
                name = input(f"Enter name for Player {i+1}: ")
                pid = register_player(db, game_id, name)
                print(f"Registered {name} with ID {pid}")

        # --- 2. DYNAMIC COMMAND HUB ---
        hub_active = True
        while hub_active:
            print(f"\n--- MAIN CONTROL HUB (Game #{game_id}) ---")
            print("[1] Run a Player Turn")
            print("[2] View All Active Players")
            print("[3] ADMIN: Register New Player Mid-Game")
            print("[4] ADMIN: Eliminate/Remove Player")
            print("[5] ADMIN: Add New Property Space")
            print("[6] ADMIN: Demolish Existing Property")
            print("[7] ADMIN: Add new action boardspace (chance, chest, tax, jail, free)")
            print("[8] ADMIN: Reset game")
            print("[9] ADMIN: End game")
            print("[10] ADMIN: Delete all game data from server")
            print("[0] Shutdown Simulation")
            
            choice = input("\nSelect Command: ")

            if choice == '1':
                # Quick check for game status before calling turn logic
                cursor = db.get_cursor()
                cursor.execute("SELECT status FROM game WHERE game_id = %s", (game_id,))
                status_row = cursor.fetchone()
                cursor.close()

                if status_row and status_row['status'] == 'finished':
                    print("\n🚫 ACCESS DENIED: This game has already ended.")
                    print("You can view stats, but no more turns can be played.")
                # Fetch only players who aren't eliminated or bankrupt
                else:
                    cursor = db.get_cursor()
                    cursor.execute("""
                        SELECT player_id, name, balance 
                        FROM player 
                        WHERE game_id = %s AND isEliminated = FALSE AND isBankrupt = FALSE
                    """, (game_id,))
                    active_list = cursor.fetchall()
                    cursor.close()

                    if not active_list:
                        print("No active players available to take a turn!")
                        continue

                    print("\nSelect Player for turn:")
                    for idx, p in enumerate(active_list):
                        print(f"[{idx+1}] {p['name']} (ID: {p['player_id']})")
                    
                    try:
                        p_choice = int(input("Choice: "))
                        if 1 <= p_choice <= len(active_list):
                            selected_player = active_list[p_choice-1]
                            interactive_turn(db, game_id, selected_player)
                        else:
                            print("Invalid selection.")
                    except ValueError:
                        print("Invalid input. Please enter a number.")

            elif choice == '2':
                view_all_players_summary(db, game_id)

            elif choice == '3':
                name = input("Enter name for new player: ")
                pid = register_player(db, game_id, name)
                print(f"Player {name} (ID: {pid}) has entered the simulation.")

            elif choice == '4':
                try:
                    target_id = int(input("Enter Player ID to forcefully eliminate: "))
                    admin_eliminate_player(db, game_id, target_id)
                except ValueError:
                    print("Invalid ID format.")

            elif choice == '5':
                try:
                    idx = int(input("Enter Board Index (0-39): "))
                    name = input("Property Name: ")
                    pset = input("Set Color/Type: ")
                    cost = int(input("Purchase Cost: "))
                    rent = int(input("Base Rent: "))
                    # FIX: Added game_id as the second argument
                    admin_add_property(db, game_id, idx, name, pset, cost, rent)
                except ValueError:
                    print("Invalid number entered. Action aborted.")

            elif choice == '6':
                try:
                    s_id = int(input("Enter Space ID to demolish: "))
                    admin_remove_property(db, game_id, s_id)
                except ValueError:
                    print("Invalid ID format.")

            elif choice == '7':
                admin_add_special_space(db, game_id)

            elif choice == '8':
                print(f"\n⚠️ WARNING: This will reset all players in Game #{game_id} to $1500, ")
                print("remove all ownership, and wipe the transaction history.")
                confirm = input("Are you absolutely sure? (y/n): ")
                
                if confirm.lower() == 'y':
                    # This calls the function I provided in the previous step
                    reset_game_state(db, game_id)
                else:
                    print("Reset cancelled.")
            
            elif choice == '9':
                confirm = input(f"End Game #{game_id}? No more turns will be allowed. (y/n): ")
                if confirm.lower() == 'y':
                    end_game_session(db, game_id)

            elif choice == '10':
                print(f"‼️ DANGER: This will permanently DELETE Game #{game_id} from the database.")
                confirm = input("Type 'DELETE' to confirm: ")
                if confirm == 'DELETE':
                    delete_game_completely(db, game_id)
                    hub_active = False # Exit the hub since the game no longer exists
            
            elif choice == '0':
                print("Shutting down simulation...")
                hub_active = False
            else:
                print("Unknown command. Please select a valid option.")

    except Exception as e:
        print(f"System Crash: {e}")
    finally:
        db.close()


def view_all_players_summary(db, game_id):
    cursor = db.get_cursor()
    cursor.execute("""
        SELECT p.player_id, p.name, p.balance, b.index_no 
        FROM player p
        JOIN boardspace b ON p.position = b.space_id
        WHERE p.game_id = %s AND p.isEliminated = FALSE
    """, (game_id,))
    players = cursor.fetchall()
    print("\n--- Current Player Standings ---")
    for p in players:
        print(f"ID: {p['player_id']} | {p['name']} | Balance: ${p['balance']} | Index: {p['index_no']}")
    cursor.close()


if __name__ == "__main__":
    start_interactive_session()