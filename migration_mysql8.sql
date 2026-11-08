-- HISTORICAL SNAPSHOT - DO NOT USE FOR DEPLOYMENTS
--
-- This dump is stale and predates loja migrations 0009 and 0010.
-- It also contains DROP TABLE statements. Use "python manage.py migrate"
-- against a new database instead. Regenerate this file only as an explicit
-- backup artifact after verifying the migration state.
--
-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: ecommerce_inteligente
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `ecommerce_inteligente`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `ecommerce_inteligente` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `ecommerce_inteligente`;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=53 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add produto',7,'add_produto'),(26,'Can change produto',7,'change_produto'),(27,'Can delete produto',7,'delete_produto'),(28,'Can view produto',7,'view_produto'),(29,'Can add venda',8,'add_venda'),(30,'Can change venda',8,'change_venda'),(31,'Can delete venda',8,'delete_venda'),(32,'Can view venda',8,'view_venda'),(33,'Can add perfil',9,'add_perfil'),(34,'Can change perfil',9,'change_perfil'),(35,'Can delete perfil',9,'delete_perfil'),(36,'Can view perfil',9,'view_perfil'),(37,'Can add pedido',10,'add_pedido'),(38,'Can change pedido',10,'change_pedido'),(39,'Can delete pedido',10,'delete_pedido'),(40,'Can view pedido',10,'view_pedido'),(41,'Can add item pedido',11,'add_itempedido'),(42,'Can change item pedido',11,'change_itempedido'),(43,'Can delete item pedido',11,'delete_itempedido'),(44,'Can view item pedido',11,'view_itempedido'),(45,'Can add categoria',12,'add_categoria'),(46,'Can change categoria',12,'change_categoria'),(47,'Can delete categoria',12,'delete_categoria'),(48,'Can view categoria',12,'view_categoria'),(49,'Can add sub categoria',13,'add_subcategoria'),(50,'Can change sub categoria',13,'change_subcategoria'),(51,'Can delete sub categoria',13,'delete_subcategoria'),(52,'Can view sub categoria',13,'view_subcategoria');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$600000$KiBcXsPMUCWKjECdBNAzcx$oZMojSlskh1IVoA0G/8HgpFv9Q/SKHGFVSuxwGj61xg=','2026-09-01 20:42:28.138891',1,'Justino','Justino','Admin','Justino@gmail.com',1,1,'2026-08-31 10:59:48.814915');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2026-09-01 20:44:37.194970','2','Manga',1,'[{\"added\": {}}]',7,1),(2,'2026-09-01 21:15:59.501165','1','Teste',3,'',12,1),(3,'2026-09-01 22:23:36.740458','52','Sorvete de Chocolate',2,'[{\"changed\": {\"fields\": [\"Em promocao\"]}}]',7,1),(4,'2026-09-01 23:12:33.820711','35','Feijão Carioca',2,'[{\"changed\": {\"fields\": [\"Em promocao\"]}}]',7,1),(5,'2026-09-01 23:13:42.174118','35','Feijão Carioca',2,'[{\"changed\": {\"fields\": [\"Em promocao\"]}}]',7,1),(6,'2026-09-01 23:15:48.840321','36','Óleo de Soja',2,'[{\"changed\": {\"fields\": [\"Em promocao\"]}}]',7,1);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'auth','user'),(5,'contenttypes','contenttype'),(12,'loja','categoria'),(11,'loja','itempedido'),(10,'loja','pedido'),(9,'loja','perfil'),(7,'loja','produto'),(13,'loja','subcategoria'),(8,'loja','venda'),(6,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-08-31 10:20:44.312959'),(2,'auth','0001_initial','2026-08-31 10:20:44.703591'),(3,'admin','0001_initial','2026-08-31 10:20:44.803925'),(4,'admin','0002_logentry_remove_auto_add','2026-08-31 10:20:44.835285'),(5,'admin','0003_logentry_add_action_flag_choices','2026-08-31 10:20:44.851393'),(6,'contenttypes','0002_remove_content_type_name','2026-08-31 10:20:44.905528'),(7,'auth','0002_alter_permission_name_max_length','2026-08-31 10:20:44.952556'),(8,'auth','0003_alter_user_email_max_length','2026-08-31 10:20:44.971798'),(9,'auth','0004_alter_user_username_opts','2026-08-31 10:20:44.986739'),(10,'auth','0005_alter_user_last_login_null','2026-08-31 10:20:45.030858'),(11,'auth','0006_require_contenttypes_0002','2026-08-31 10:20:45.034361'),(12,'auth','0007_alter_validators_add_error_messages','2026-08-31 10:20:45.056042'),(13,'auth','0008_alter_user_username_max_length','2026-08-31 10:20:45.075518'),(14,'auth','0009_alter_user_last_name_max_length','2026-08-31 10:20:45.099133'),(15,'auth','0010_alter_group_name_max_length','2026-08-31 10:20:45.118170'),(16,'auth','0011_update_proxy_permissions','2026-08-31 10:20:45.152166'),(17,'auth','0012_alter_user_first_name_max_length','2026-08-31 10:20:45.173782'),(18,'loja','0001_initial','2026-08-31 10:20:45.366611'),(19,'loja','0002_auto_20260227_1201','2026-08-31 10:20:45.749330'),(20,'loja','0003_produto_imagem','2026-08-31 10:20:45.759188'),(21,'loja','0004_perfil','2026-08-31 10:20:45.824739'),(22,'loja','0005_produto_em_promocao_produto_preco_promocional_and_more','2026-08-31 10:20:46.052410'),(23,'loja','0006_perfil_bairro_perfil_municipio_perfil_provincia_and_more','2026-08-31 10:20:46.171802'),(24,'loja','0007_categoria_alter_perfil_bairro_alter_perfil_municipio_and_more','2026-08-31 10:20:46.560312'),(25,'sessions','0001_initial','2026-08-31 10:20:46.592355'),(26,'loja','0008_subcategoria_produto_subcategoria','2026-09-01 21:29:36.942817');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('qi8fh8y3uxmwf3m1a5fo10t2mtovp9h1','eyJjYXJyaW5obyI6eyIzNSI6MX19:1x1fsL:XAMC7_dWJCvTOkwoJGZSiq6eNvdNs2Uwz8ihtZkVSjE','2026-09-16 07:59:17.314591'),('qqvgup4peer36ax25w89q5wgek726i6l','.eJzNlsGO2yAURX_FYh0nOCax413bRTetVKmabupRhAHHzGATgZlqGuXfC3FGmpA4cVpZ6soy73LNPTwjdmCNTVutjWZqzSnIQAQm78cKTJ5Z4wr0CTcbOSWyaRUvpk4yPVb19KukTHw8ak8MKqwrZwvniNCUptESp2gJU7SYrxYsQTBG5YKxcoUohRFMYrhkNJlDgpKlHcElpGlaImdas8Zo6_Vzl4MG1ywHWZCDD6ZlTcsJznMDIUu6RywDFtiSVPy3X8nBxM7jNknnUGIdlDjUFWeChli0naB2mbSTnH7wszJbqXtMXGYdErnp6kaJrjzDtObNzHGZbZQ021knwJQ-9Gts9agrFMOUKFMXF1Y0CoL9JPir2PtHp2CcOkEE4dw3emi5sCuiUrELdurN7gpAV77B7yD5n_ANTu3zi_2ByLf-Ip9wjyXhigh2vZ8_4ZZtbErct7kCvzIVHjry8qYIu4AZebPp3xlPN3B7BsTzidwXyQe88O2-Mcrppd4_Y3yRzPYw_QaWo2g8JsNC-CyW5zaq5OIfWLjpN1kcRGOyGBLCZ5Gc2ShJ7QHR12S6ktstbzZhgfUza69R6YxuYTmqRuRyZyCfUOobfjdFQK78jMOaRpti6OlyIh0P1F25fEor3-2HvTX1HlW1bNhrWHAhwl_45RqmF2dzg0-nGQ_MfVE8MhH0UaH9o735EawUbyoJsh2IVyCLJiBegGw-ASjt3pB97Pd_ABGJbSE:1x1g61:h7Yq6ypg2xz69RMxFlViWT-_TuGv3sTtFOoyMh4WSDs','2026-09-16 08:13:25.077081');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_categoria`
--

DROP TABLE IF EXISTS `loja_categoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_categoria` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `slug` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_categoria`
--

LOCK TABLES `loja_categoria` WRITE;
/*!40000 ALTER TABLE `loja_categoria` DISABLE KEYS */;
INSERT INTO `loja_categoria` VALUES (2,'Mercearia e Despensa','mercearia-e-despensa'),(3,'Produtos Frescos','produtos-frescos'),(4,'Bebidas','bebidas'),(5,'Higiene e Casa','higiene-e-casa'),(6,'Matabicho','matabicho'),(7,'Frio e Congelados','frio-e-congelados'),(10,'Higiene e Casa Teste Unique 2','higiene-e-casa-teste-unique-2');
/*!40000 ALTER TABLE `loja_categoria` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_itempedido`
--

DROP TABLE IF EXISTS `loja_itempedido`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_itempedido` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `quantidade` int(10) unsigned NOT NULL CHECK (`quantidade` >= 0),
  `produto_id` bigint(20) NOT NULL,
  `pedido_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `loja_itempedido_produto_id_28d33f8b_fk_loja_produto_id` (`produto_id`),
  KEY `loja_itempedido_pedido_id_f4c62b89_fk_loja_pedido_id` (`pedido_id`),
  CONSTRAINT `loja_itempedido_pedido_id_f4c62b89_fk_loja_pedido_id` FOREIGN KEY (`pedido_id`) REFERENCES `loja_pedido` (`id`),
  CONSTRAINT `loja_itempedido_produto_id_28d33f8b_fk_loja_produto_id` FOREIGN KEY (`produto_id`) REFERENCES `loja_produto` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_itempedido`
--

LOCK TABLES `loja_itempedido` WRITE;
/*!40000 ALTER TABLE `loja_itempedido` DISABLE KEYS */;
/*!40000 ALTER TABLE `loja_itempedido` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_pedido`
--

DROP TABLE IF EXISTS `loja_pedido`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_pedido` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `data_criacao` datetime(6) NOT NULL,
  `finalizado` tinyint(1) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `loja_pedido_usuario_id_fa3884ee_fk_auth_user_id` (`usuario_id`),
  CONSTRAINT `loja_pedido_usuario_id_fa3884ee_fk_auth_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_pedido`
--

LOCK TABLES `loja_pedido` WRITE;
/*!40000 ALTER TABLE `loja_pedido` DISABLE KEYS */;
/*!40000 ALTER TABLE `loja_pedido` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_perfil`
--

DROP TABLE IF EXISTS `loja_perfil`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_perfil` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `saldo_bonus` decimal(10,2) NOT NULL,
  `total_compras_realizadas` int(10) unsigned NOT NULL CHECK (`total_compras_realizadas` >= 0),
  `usuario_id` int(11) NOT NULL,
  `bairro` varchar(50) DEFAULT NULL,
  `municipio` varchar(50) DEFAULT NULL,
  `provincia` varchar(50) DEFAULT NULL,
  `telefone` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `loja_perfil_usuario_id_bc8a9aef_fk_auth_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_perfil`
--

LOCK TABLES `loja_perfil` WRITE;
/*!40000 ALTER TABLE `loja_perfil` DISABLE KEYS */;
INSERT INTO `loja_perfil` VALUES (1,4880.00,0,1,NULL,NULL,NULL,NULL);
/*!40000 ALTER TABLE `loja_perfil` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_produto`
--

DROP TABLE IF EXISTS `loja_produto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_produto` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `categoria_id` bigint(20) DEFAULT NULL,
  `preco` decimal(10,2) NOT NULL,
  `quantidade_estoque` int(11) NOT NULL,
  `data_validade` date DEFAULT NULL,
  `status_promocao` tinyint(1) NOT NULL,
  `imagem` varchar(100) DEFAULT NULL,
  `em_promocao` tinyint(1) NOT NULL,
  `preco_promocional` decimal(10,2) DEFAULT NULL,
  `subcategoria_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `loja_produto_categoria_id_8dd6019e` (`categoria_id`),
  KEY `loja_produto_subcategoria_id_171c3cf5_fk_loja_subcategoria_id` (`subcategoria_id`),
  CONSTRAINT `loja_produto_categoria_id_8dd6019e_fk_loja_categoria_id` FOREIGN KEY (`categoria_id`) REFERENCES `loja_categoria` (`id`),
  CONSTRAINT `loja_produto_subcategoria_id_171c3cf5_fk_loja_subcategoria_id` FOREIGN KEY (`subcategoria_id`) REFERENCES `loja_subcategoria` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_produto`
--

LOCK TABLES `loja_produto` WRITE;
/*!40000 ALTER TABLE `loja_produto` DISABLE KEYS */;
INSERT INTO `loja_produto` VALUES (34,'Arroz de Angola',2,3200.00,14,NULL,0,'',0,NULL,1),(35,'Feijão Carioca',2,2900.00,8,NULL,1,'',1,2320.00,1),(36,'Óleo de Soja',2,2600.00,17,NULL,1,'',1,2080.00,2),(37,'Sardinhas',2,1800.00,12,NULL,0,'',0,NULL,3),(38,'Carne de Vaca',3,5200.00,5,NULL,0,'',0,NULL,4),(39,'Peixe do Dia',3,4800.00,11,NULL,0,'',0,NULL,5),(40,'Maçã',3,2100.00,29,NULL,0,'',0,NULL,6),(41,'Pão Frances',3,2300.00,24,NULL,0,'',0,NULL,7),(42,'Água Mineral',4,1500.00,25,NULL,0,'',0,NULL,8),(43,'Cerveja Premium',4,2800.00,15,NULL,0,'',0,NULL,9),(44,'Vinho Tinto',4,6200.00,7,NULL,0,'',0,NULL,10),(45,'Sabonete em Barra',5,1800.00,21,NULL,0,'',0,NULL,11),(46,'Detergente',5,2200.00,20,NULL,0,'',0,NULL,12),(47,'Coleira para Cães',5,1700.00,14,NULL,0,'',0,NULL,13),(48,'Café Torrado',6,2300.00,14,NULL,0,'',0,NULL,14),(49,'Papa de Milho',6,2000.00,16,NULL,0,'',0,NULL,15),(50,'Biscoito de Chocolate',6,1600.00,26,NULL,0,'',0,NULL,16),(51,'Refeição Pronta',7,3500.00,11,NULL,0,'',0,NULL,17),(52,'Sorvete de Chocolate',7,1900.00,18,NULL,0,'',0,NULL,18),(53,'Detergente Teste 2',10,120.00,5,NULL,0,'',0,NULL,19);
/*!40000 ALTER TABLE `loja_produto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_subcategoria`
--

DROP TABLE IF EXISTS `loja_subcategoria`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_subcategoria` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `slug` varchar(50) DEFAULT NULL,
  `categoria_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `loja_subcategoria_categoria_id_3cf5848d_fk_loja_categoria_id` (`categoria_id`),
  CONSTRAINT `loja_subcategoria_categoria_id_3cf5848d_fk_loja_categoria_id` FOREIGN KEY (`categoria_id`) REFERENCES `loja_categoria` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_subcategoria`
--

LOCK TABLES `loja_subcategoria` WRITE;
/*!40000 ALTER TABLE `loja_subcategoria` DISABLE KEYS */;
INSERT INTO `loja_subcategoria` VALUES (1,'Arroz, Massas e Grãos','arroz-massas-e-graos',2),(2,'Óleos e Azeites','oleos-e-azeites',2),(3,'Enlatados','enlatados',2),(4,'Talho e Carnes','talho-e-carnes',3),(5,'Peixaria','peixaria',3),(6,'Frutas e Vegetais','frutas-e-vegetais',3),(7,'Padaria','padaria',3),(8,'Águas e Sumos','aguas-e-sumos',4),(9,'Cervejas','cervejas',4),(10,'Vinhos e Espirituosas','vinhos-e-espirituosas',4),(11,'Higiene Pessoal','higiene-pessoal',5),(12,'Limpeza da Casa','limpeza-da-casa',5),(13,'Mundo Pet','mundo-pet',5),(14,'Cafés e Chás','cafes-e-chas',6),(15,'Cereais e Papas','cereais-e-papas',6),(16,'Bolachas e Doces','bolachas-e-doces',6),(17,'Refeições Prontas','refeicoes-prontas',7),(18,'Gelados','gelados',7),(19,'Limpeza da Casa Teste Unique 2','limpeza-da-casa-teste-unique-2',10);
/*!40000 ALTER TABLE `loja_subcategoria` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loja_venda`
--

DROP TABLE IF EXISTS `loja_venda`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `loja_venda` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_transacao` bigint(20) NOT NULL,
  `data_venda` datetime(6) NOT NULL,
  `produto_id` bigint(20) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `loja_venda_usuario_id_d320dfcc_fk_auth_user_id` (`usuario_id`),
  KEY `loja_venda_produto_id_57b1d9ba_fk` (`produto_id`),
  CONSTRAINT `loja_venda_produto_id_57b1d9ba_fk` FOREIGN KEY (`produto_id`) REFERENCES `loja_produto` (`id`),
  CONSTRAINT `loja_venda_usuario_id_d320dfcc_fk_auth_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loja_venda`
--

LOCK TABLES `loja_venda` WRITE;
/*!40000 ALTER TABLE `loja_venda` DISABLE KEYS */;
INSERT INTO `loja_venda` VALUES (5,1788299470,'2026-09-01 21:51:10.271046',34,1),(6,1788299470,'2026-09-01 21:51:10.275308',39,1),(7,1788299470,'2026-09-01 21:51:10.286079',38,1),(8,1788299470,'2026-09-01 21:51:10.289843',43,1),(9,1788299470,'2026-09-01 21:51:10.292495',44,1),(10,1788299470,'2026-09-01 21:51:10.294837',45,1),(11,1788299470,'2026-09-01 21:51:10.298072',48,1),(12,1788299470,'2026-09-01 21:51:10.299096',48,1),(13,1788299470,'2026-09-01 21:51:10.300084',48,1),(14,1788299470,'2026-09-01 21:51:10.302562',48,1),(15,1788303457,'2026-09-01 22:57:37.575941',35,1),(16,1788303457,'2026-09-01 22:57:37.585487',35,1),(17,1788303457,'2026-09-01 22:57:37.588415',35,1),(18,1788303457,'2026-09-01 22:57:37.592466',35,1),(19,1788303457,'2026-09-01 22:57:37.602170',35,1),(20,1788303457,'2026-09-01 22:57:37.607817',35,1),(21,1788303457,'2026-09-01 22:57:37.610670',35,1),(22,1788303457,'2026-09-01 22:57:37.612306',35,1),(23,1788303457,'2026-09-01 22:57:37.620762',35,1),(24,1788303457,'2026-09-01 22:57:37.627498',36,1),(25,1788303457,'2026-09-01 22:57:37.628205',36,1),(26,1788303457,'2026-09-01 22:57:37.628755',36,1),(27,1788303457,'2026-09-01 22:57:37.637764',38,1),(28,1788303457,'2026-09-01 22:57:37.641443',38,1),(29,1788303457,'2026-09-01 22:57:37.644114',38,1),(30,1788303457,'2026-09-01 22:57:37.645095',38,1),(31,1788303532,'2026-09-01 22:58:52.277858',35,1),(32,1788303532,'2026-09-01 22:58:52.286014',40,1),(33,1788303532,'2026-09-01 22:58:52.297162',52,1),(34,1788303532,'2026-09-01 22:58:52.316906',49,1);
/*!40000 ALTER TABLE `loja_venda` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'ecommerce_inteligente'
--

--
-- Dumping routines for database 'ecommerce_inteligente'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-02 10:19:47
