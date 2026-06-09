-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: monopoly_db
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `boardspace`
--

DROP TABLE IF EXISTS `boardspace`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `boardspace` (
  `space_id` int NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `index_no` int DEFAULT NULL,
  `type` varchar(20) DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  PRIMARY KEY (`space_id`),
  UNIQUE KEY `game_id` (`game_id`,`index_no`),
  UNIQUE KEY `uq_boardspace_index` (`index_no`),
  CONSTRAINT `boardspace_ibfk_1` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `chk_boardspace_index` CHECK ((`index_no` between 0 and 39)),
  CONSTRAINT `chk_boardspace_type` CHECK ((`type` in (_utf8mb4'property',_utf8mb4'jail',_utf8mb4'chance',_utf8mb4'chest',_utf8mb4'start',_utf8mb4'tax',_utf8mb4'free')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `boardspace`
--

LOCK TABLES `boardspace` WRITE;
/*!40000 ALTER TABLE `boardspace` DISABLE KEYS */;
INSERT INTO `boardspace` VALUES (0,'Start',0,'start',1),(1,'Salvador',1,'property',1),(2,'Community Chest',2,'chest',1),(3,'Rio',3,'property',1),(4,'Income Tax',4,'tax',1),(5,'TLV Airport',5,'property',1),(6,'Tel Aviv',6,'property',1),(7,'Chance',7,'chance',1),(8,'Haifa',8,'property',1),(9,'Jerusalem',9,'property',1),(10,'Jail',10,'jail',1),(11,'Venice',11,'property',1),(12,'Electric Company',12,'property',1),(13,'Milan',13,'property',1),(14,'Rome',14,'property',1),(15,'MUC Airport',15,'property',1),(16,'Frankfurt',16,'property',1),(17,'Community Chest',17,'chest',1),(18,'Munich',18,'property',1),(19,'Berlin',19,'property',1),(20,'Vacation',20,'free',1),(21,'Shenzhen',21,'property',1),(22,'Chance',22,'chance',1),(23,'Shanghai',23,'property',1),(24,'Beijing',24,'property',1),(25,'CDG Airport',25,'property',1),(26,'Lyon',26,'property',1),(27,'Toulouse',27,'property',1),(28,'Water Company',28,'property',1),(29,'Paris',29,'property',1),(30,'Go To Prison',30,'jail',1),(31,'Liverpool',31,'property',1),(32,'Manchester',32,'property',1),(33,'Treasure',33,'chest',1),(34,'London',34,'property',1),(35,'JFK Airport',35,'property',1),(36,'Chance',36,'chance',1),(37,'San Francisco',37,'property',1),(38,'Premium Tax',38,'tax',1),(39,'New York',39,'property',1);
/*!40000 ALTER TABLE `boardspace` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `game`
--

DROP TABLE IF EXISTS `game`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `game` (
  `game_id` int NOT NULL AUTO_INCREMENT,
  `status` varchar(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL,
  PRIMARY KEY (`game_id`),
  CONSTRAINT `game_chk_1` CHECK ((`status` in (_utf8mb4'waiting',_utf8mb4'running',_utf8mb4'finished')))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `game`
--

LOCK TABLES `game` WRITE;
/*!40000 ALTER TABLE `game` DISABLE KEYS */;
INSERT INTO `game` VALUES (1,'running','2026-02-04 04:54:48'),(2,'running','2026-03-19 06:04:03'),(3,'running','2026-03-19 06:49:58'),(4,'running','2026-03-19 08:51:23');
/*!40000 ALTER TABLE `game` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `log`
--

DROP TABLE IF EXISTS `log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `log` (
  `log_id` int NOT NULL AUTO_INCREMENT,
  `eventType` varchar(20) DEFAULT NULL,
  `eventDescription` text,
  `event_time` timestamp NULL DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  `player_id` int DEFAULT NULL,
  PRIMARY KEY (`log_id`),
  KEY `player_id` (`player_id`),
  KEY `log_ibfk_1` (`game_id`),
  CONSTRAINT `log_ibfk_1` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `log_ibfk_2` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `chk_log_eventType` CHECK ((`eventType` in (_utf8mb4'trade',_utf8mb4'movement',_utf8mb4'transaction',_utf8mb4'rent',_utf8mb4'chance',_utf8mb4'chest',_utf8mb4'system')))
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log`
--

LOCK TABLES `log` WRITE;
/*!40000 ALTER TABLE `log` DISABLE KEYS */;
INSERT INTO `log` VALUES (18,'transaction','Player 5 bought Tel Aviv for $100','2026-03-19 06:05:29',2,NULL),(19,'rent','Player 4 paid $6 rent to Player 5','2026-03-19 06:24:44',2,NULL),(20,'trade','Trade #1 accepted between Player 4 and Player 5.','2026-03-19 06:33:50',2,NULL),(21,'transaction','Player 9 bought Haifa for $100','2026-03-19 06:53:30',3,NULL),(22,'transaction','Player 9 mortgaged Haifa','2026-03-19 06:57:52',3,NULL),(23,'transaction','Player 6 bought TLV Airport for $200','2026-03-19 07:02:15',2,NULL),(24,'transaction','Player 6 bought Frankfurt for $180','2026-03-19 07:05:09',2,NULL),(25,'transaction','Player 4 bought Munich for $180','2026-03-19 07:10:51',2,NULL),(26,'trade','Trade #2 accepted between Player 4 and Player 6.','2026-03-19 07:13:45',2,NULL);
/*!40000 ALTER TABLE `log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ownership`
--

DROP TABLE IF EXISTS `ownership`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ownership` (
  `ownership_id` int NOT NULL AUTO_INCREMENT,
  `start_time` timestamp NULL DEFAULT NULL,
  `end_time` timestamp NULL DEFAULT NULL,
  `player_id` int NOT NULL,
  `property_id` int NOT NULL,
  PRIMARY KEY (`ownership_id`,`player_id`,`property_id`),
  KEY `player_id` (`player_id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `ownership_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `ownership_ibfk_2` FOREIGN KEY (`property_id`) REFERENCES `property` (`property_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ownership`
--

LOCK TABLES `ownership` WRITE;
/*!40000 ALTER TABLE `ownership` DISABLE KEYS */;
INSERT INTO `ownership` VALUES (8,'2026-03-19 06:05:29','2026-03-19 06:33:50',5,4),(9,'2026-03-19 06:33:50','2026-03-19 07:13:45',4,4),(10,'2026-03-19 06:53:30',NULL,9,5),(11,'2026-03-19 07:02:15','2026-03-19 07:13:45',6,3),(12,'2026-03-19 07:05:09',NULL,6,12),(13,'2026-03-19 07:10:51',NULL,4,13),(14,'2026-03-19 07:13:45',NULL,6,4),(15,'2026-03-19 07:13:45',NULL,4,3);
/*!40000 ALTER TABLE `ownership` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `player`
--

DROP TABLE IF EXISTS `player`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `player` (
  `player_id` int NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `balance` int DEFAULT NULL,
  `position` int DEFAULT NULL,
  `inJail` tinyint(1) DEFAULT NULL,
  `jailTurns` int DEFAULT NULL,
  `isBankrupt` tinyint(1) DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  `isEliminated` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`player_id`),
  KEY `position` (`position`),
  KEY `player_ibfk_2` (`game_id`),
  CONSTRAINT `player_ibfk_1` FOREIGN KEY (`position`) REFERENCES `boardspace` (`space_id`),
  CONSTRAINT `player_ibfk_2` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `player_chk_2` CHECK ((`jailTurns` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `player`
--

LOCK TABLES `player` WRITE;
/*!40000 ALTER TABLE `player` DISABLE KEYS */;
INSERT INTO `player` VALUES (1,'Saksham',1500,0,0,0,0,1,0),(2,'Aryan',1500,0,0,0,0,1,0),(3,'Mohman',1500,0,0,0,0,1,0),(4,'Aryan2',1234,18,0,0,0,2,0),(5,'Saksham2',1486,39,0,0,0,2,0),(6,'Mohman2',1120,16,0,0,0,2,0),(7,'Brawler21',1500,0,0,0,0,3,0),(8,'RascalWontShoot',1500,0,0,0,0,3,0),(9,'BlazeDanger',1450,18,0,0,0,3,0),(10,'sdhg',1500,0,0,0,0,4,0),(11,'geda',1500,0,0,0,0,4,0),(12,'hfs',1500,0,0,0,0,4,0),(13,'gs',1500,0,0,0,0,4,0);
/*!40000 ALTER TABLE `player` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `property`
--

DROP TABLE IF EXISTS `property`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `property` (
  `property_id` int NOT NULL,
  `propSet` varchar(20) DEFAULT NULL,
  `cost` int DEFAULT NULL,
  `rent` int DEFAULT NULL,
  `rent_1` int DEFAULT NULL,
  `rent_2` int DEFAULT NULL,
  `rent_3` int DEFAULT NULL,
  `rent_4` int DEFAULT NULL,
  `rent_h` int DEFAULT NULL,
  `isMortgaged` tinyint(1) DEFAULT NULL,
  `houses` int DEFAULT '0',
  `name` varchar(50) DEFAULT NULL,
  `space_id` int DEFAULT NULL,
  `houseCost` int NOT NULL,
  PRIMARY KEY (`property_id`),
  KEY `fk_property_space` (`space_id`),
  CONSTRAINT `fk_property_space` FOREIGN KEY (`space_id`) REFERENCES `boardspace` (`space_id`),
  CONSTRAINT `property_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `boardspace` (`space_id`),
  CONSTRAINT `chk_houseCost` CHECK ((`houseCost` >= 0)),
  CONSTRAINT `chk_houses_range` CHECK ((`houses` between 0 and 5)),
  CONSTRAINT `chk_rent` CHECK ((`rent` >= 0)),
  CONSTRAINT `chk_rent1` CHECK ((`rent_1` >= 0)),
  CONSTRAINT `chk_rent2` CHECK ((`rent_2` >= 0)),
  CONSTRAINT `chk_rent3` CHECK ((`rent_3` >= 0)),
  CONSTRAINT `chk_rent4` CHECK ((`rent_4` >= 0)),
  CONSTRAINT `chk_renth` CHECK ((`rent_h` >= 0)),
  CONSTRAINT `property_chk_1` CHECK ((`cost` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `property`
--

LOCK TABLES `property` WRITE;
/*!40000 ALTER TABLE `property` DISABLE KEYS */;
INSERT INTO `property` VALUES (1,'brazil',60,2,10,30,90,160,250,0,0,'Salvador',1,50),(2,'brazil',60,4,20,60,180,320,450,0,0,'Rio',3,50),(3,'airport',200,25,50,100,200,NULL,NULL,0,0,'TLV Airport',5,0),(4,'israel',100,6,30,90,270,400,550,0,0,'Tel Aviv',6,50),(5,'israel',100,6,30,90,270,400,550,1,0,'Haifa',8,50),(6,'israel',120,8,40,100,300,450,600,0,0,'Jerusalem',9,50),(7,'italy',140,10,50,150,450,625,750,0,0,'Venice',11,100),(8,'company',150,4,10,NULL,NULL,NULL,NULL,0,0,'Electric Company',12,0),(9,'italy',140,10,50,150,450,625,750,0,0,'Milan',13,100),(10,'italy',160,12,60,180,500,700,900,0,0,'Rome',14,100),(11,'airport',200,25,50,100,200,NULL,NULL,0,0,'MUC Airport',15,0),(12,'germany',180,14,70,200,550,750,950,0,0,'Frankfurt',16,100),(13,'germany',180,14,70,200,550,750,950,0,0,'Munich',18,100),(14,'germany',200,16,80,220,600,800,1000,0,0,'Berlin',19,100),(21,'China',220,18,90,250,700,875,1050,0,0,'Shenzhen',21,150),(22,'China',220,18,90,250,700,875,1050,0,0,'Beijing',22,150),(24,'China',240,20,100,300,750,925,1100,0,0,'Shanghai',24,150),(25,'Airport',200,25,50,100,200,NULL,NULL,0,0,'CDG Airport',25,0),(26,'France',260,22,110,330,800,975,1150,0,0,'Lyon',26,150),(27,'France',260,22,110,330,800,975,1150,0,0,'Toulouse',27,150),(28,'Company',150,4,NULL,NULL,NULL,NULL,NULL,0,0,'Water Company',28,0),(29,'France',280,24,120,360,850,1025,1200,0,0,'Paris',29,150),(31,'UK',300,26,130,390,900,1100,1275,0,0,'Liverpool',31,200),(32,'UK',300,26,130,390,900,1100,1275,0,0,'Manchester',32,200),(34,'UK',320,28,150,450,1000,1200,1400,0,0,'London',34,200),(35,'Airport',200,25,50,100,200,NULL,NULL,0,0,'JFK Airport',35,0),(37,'USA',350,35,175,500,1100,1300,1500,0,0,'San Francisco',37,200),(39,'USA',400,50,200,600,1400,1700,2000,0,0,'New York',39,200);
/*!40000 ALTER TABLE `property` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trade`
--

DROP TABLE IF EXISTS `trade`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade` (
  `trade_id` int NOT NULL,
  `status` varchar(20) DEFAULT NULL,
  `offeredCash` int DEFAULT NULL,
  `requestedCash` int DEFAULT NULL,
  `negotiationRound` int DEFAULT NULL,
  `proposer_id` int DEFAULT NULL,
  `receiver_id` int DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  PRIMARY KEY (`trade_id`),
  KEY `proposer_id` (`proposer_id`),
  KEY `receiver_id` (`receiver_id`),
  KEY `trade_ibfk_3` (`game_id`),
  CONSTRAINT `trade_ibfk_1` FOREIGN KEY (`proposer_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `trade_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `trade_ibfk_3` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `trade_chk_1` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'accepted',_utf8mb4'declined'))),
  CONSTRAINT `trade_chk_2` CHECK ((`offeredCash` >= 0)),
  CONSTRAINT `trade_chk_3` CHECK ((`requestedCash` >= 0)),
  CONSTRAINT `trade_chk_4` CHECK ((`negotiationRound` >= 0)),
  CONSTRAINT `trade_chk_5` CHECK ((`proposer_id` <> `receiver_id`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trade`
--

LOCK TABLES `trade` WRITE;
/*!40000 ALTER TABLE `trade` DISABLE KEYS */;
INSERT INTO `trade` VALUES (1,'accepted',80,0,0,4,5,2),(2,'accepted',0,0,0,4,6,2);
/*!40000 ALTER TABLE `trade` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trade_offers`
--

DROP TABLE IF EXISTS `trade_offers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade_offers` (
  `trade_id` int NOT NULL,
  `property_id` int NOT NULL,
  PRIMARY KEY (`trade_id`,`property_id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `trade_offers_ibfk_1` FOREIGN KEY (`trade_id`) REFERENCES `trade` (`trade_id`),
  CONSTRAINT `trade_offers_ibfk_2` FOREIGN KEY (`property_id`) REFERENCES `property` (`property_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trade_offers`
--

LOCK TABLES `trade_offers` WRITE;
/*!40000 ALTER TABLE `trade_offers` DISABLE KEYS */;
INSERT INTO `trade_offers` VALUES (2,4);
/*!40000 ALTER TABLE `trade_offers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `trade_requests`
--

DROP TABLE IF EXISTS `trade_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `trade_requests` (
  `trade_id` int NOT NULL,
  `property_id` int NOT NULL,
  PRIMARY KEY (`trade_id`,`property_id`),
  KEY `property_id` (`property_id`),
  CONSTRAINT `trade_requests_ibfk_1` FOREIGN KEY (`trade_id`) REFERENCES `trade` (`trade_id`),
  CONSTRAINT `trade_requests_ibfk_2` FOREIGN KEY (`property_id`) REFERENCES `property` (`property_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `trade_requests`
--

LOCK TABLES `trade_requests` WRITE;
/*!40000 ALTER TABLE `trade_requests` DISABLE KEYS */;
INSERT INTO `trade_requests` VALUES (2,3),(1,4);
/*!40000 ALTER TABLE `trade_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transaction`
--

DROP TABLE IF EXISTS `transaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transaction` (
  `transaction_id` int NOT NULL AUTO_INCREMENT,
  `amount` int DEFAULT NULL,
  `transaction_type` varchar(20) DEFAULT NULL,
  `transaction_time` timestamp NULL DEFAULT NULL,
  `player_id` int DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  PRIMARY KEY (`transaction_id`),
  KEY `player_id` (`player_id`),
  KEY `transaction_ibfk_2` (`game_id`),
  CONSTRAINT `transaction_ibfk_1` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `transaction_ibfk_2` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `chk_amount_positive` CHECK ((`amount` > 0)),
  CONSTRAINT `chk_transaction_type` CHECK ((`transaction_type` in (_utf8mb4'salary',_utf8mb4'tax',_utf8mb4'purchase',_utf8mb4'rent',_utf8mb4'mortgage',_utf8mb4'unmortgage',_utf8mb4'fine',_utf8mb4'reward')))
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transaction`
--

LOCK TABLES `transaction` WRITE;
/*!40000 ALTER TABLE `transaction` DISABLE KEYS */;
INSERT INTO `transaction` VALUES (11,100,'purchase','2026-03-19 06:05:29',5,2),(12,6,'rent','2026-03-19 06:24:44',4,2),(13,6,'rent','2026-03-19 06:24:44',5,2),(14,80,'purchase','2026-03-19 06:33:50',4,2),(15,80,'purchase','2026-03-19 06:33:50',5,2),(16,100,'purchase','2026-03-19 06:53:30',9,3),(17,50,'mortgage','2026-03-19 06:57:52',9,3),(18,200,'purchase','2026-03-19 07:02:15',6,2),(19,180,'purchase','2026-03-19 07:05:09',6,2),(20,180,'purchase','2026-03-19 07:10:51',4,2);
/*!40000 ALTER TABLE `transaction` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `turn`
--

DROP TABLE IF EXISTS `turn`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `turn` (
  `turn_id` int NOT NULL,
  `dice1` int DEFAULT NULL,
  `dice2` int DEFAULT NULL,
  `prev_position` int DEFAULT NULL,
  `new_position` int DEFAULT NULL,
  `player_id` int DEFAULT NULL,
  `game_id` int DEFAULT NULL,
  `is_completed` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`turn_id`),
  KEY `prev_position` (`prev_position`),
  KEY `new_position` (`new_position`),
  KEY `player_id` (`player_id`),
  KEY `turn_ibfk_4` (`game_id`),
  CONSTRAINT `turn_ibfk_1` FOREIGN KEY (`prev_position`) REFERENCES `boardspace` (`space_id`),
  CONSTRAINT `turn_ibfk_2` FOREIGN KEY (`new_position`) REFERENCES `boardspace` (`space_id`),
  CONSTRAINT `turn_ibfk_3` FOREIGN KEY (`player_id`) REFERENCES `player` (`player_id`),
  CONSTRAINT `turn_ibfk_4` FOREIGN KEY (`game_id`) REFERENCES `game` (`game_id`),
  CONSTRAINT `turn_chk_1` CHECK ((`dice1` between 1 and 6)),
  CONSTRAINT `turn_chk_2` CHECK ((`dice2` between 1 and 6))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `turn`
--

LOCK TABLES `turn` WRITE;
/*!40000 ALTER TABLE `turn` DISABLE KEYS */;
INSERT INTO `turn` VALUES (1,1,5,0,6,5,2,1),(2,NULL,NULL,6,NULL,5,2,0),(3,4,5,6,15,5,2,1),(4,2,4,0,6,4,2,1),(5,2,2,15,19,5,2,1),(6,6,4,19,29,5,2,1),(7,NULL,NULL,6,NULL,4,2,0),(8,2,6,0,8,9,3,1),(9,6,4,8,18,9,3,1),(10,3,2,0,5,6,2,1),(11,5,5,29,39,5,2,1),(12,6,5,5,16,6,2,1),(13,NULL,NULL,6,NULL,4,2,0),(14,NULL,NULL,6,NULL,4,2,0),(15,6,6,6,18,4,2,1),(16,NULL,NULL,16,NULL,6,2,0);
/*!40000 ALTER TABLE `turn` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-08 12:16:43
