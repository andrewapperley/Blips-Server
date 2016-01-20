-- phpMyAdmin SQL Dump
-- version 4.1.12
-- http://www.phpmyadmin.net
--
-- Host: localhost:3306
-- Generation Time: Aug 23, 2014 at 08:46 PM
-- Server version: 5.5.34
-- PHP Version: 5.5.10

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `blips`
--
CREATE DATABASE IF NOT EXISTS `blips` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `blips`;

-- --------------------------------------------------------

--
-- Table structure for table `active_users`
--

DROP TABLE IF EXISTS `active_users`;
CREATE TABLE IF NOT EXISTS `active_users` (
  `user_id` varchar(255) NOT NULL,
  `access_token` varchar(255) DEFAULT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `active` smallint(6) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `connections`
--

DROP TABLE IF EXISTS `connections`;
CREATE TABLE IF NOT EXISTS `connections` (
  `connection_id` varchar(255) NOT NULL,
  `user1` int(11) DEFAULT NULL,
  `user2` int(11) DEFAULT NULL,
  `start_date` datetime DEFAULT NULL,
  `approved` smallint(6) DEFAULT NULL,
  `disabled` smallint(6) DEFAULT NULL,
  PRIMARY KEY (`connection_id`),
  KEY `user1` (`user1`),
  KEY `user2` (`user2`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
CREATE TABLE IF NOT EXISTS `notifications` (
  `notification_id` int(11) NOT NULL AUTO_INCREMENT,
  `notification_sender` int(11) DEFAULT NULL,
  `notification_receiver_id` int(11) DEFAULT NULL,
  `notification_payload` blob,
  `notification_date` int(11) DEFAULT NULL,
  `notification_sent` smallint(6) DEFAULT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `notification_receiver_id` (`notification_receiver_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=52 ;

-- --------------------------------------------------------

--
-- Table structure for table `notification_users`
--

DROP TABLE IF EXISTS `notification_users`;
CREATE TABLE IF NOT EXISTS `notification_users` (
  `user_id` int(11) NOT NULL,
  `registered_user_token` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `timelines`
--

DROP TABLE IF EXISTS `timelines`;
CREATE TABLE IF NOT EXISTS `timelines` (
  `timeline_id` varchar(255) NOT NULL,
  `connection_id` varchar(255) DEFAULT NULL,
  `video_count` int(11) DEFAULT NULL,
  PRIMARY KEY (`timeline_id`),
  KEY `connection_id` (`connection_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `password_salt` varchar(255) DEFAULT NULL,
  `profile_image` varchar(255) DEFAULT NULL,
  `display_name` varchar(50) DEFAULT NULL,
  `deactivated` smallint(6) DEFAULT NULL,
  `password_reset` smallint(6) DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=9 ;

-- --------------------------------------------------------

--
-- Table structure for table `videos`
--

DROP TABLE IF EXISTS `videos`;
CREATE TABLE IF NOT EXISTS `videos` (
  `date` int(11) DEFAULT NULL,
  `user` int(11) DEFAULT NULL,
  `timeline_id` varchar(255) DEFAULT NULL,
  `thumbnail` varchar(255) DEFAULT NULL,
  `description` varchar(100) DEFAULT NULL,
  `video_id` varchar(255) NOT NULL,
  PRIMARY KEY (`video_id`),
  KEY `user` (`user`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `video_favourites`
--

DROP TABLE IF EXISTS `video_favourites`;
CREATE TABLE IF NOT EXISTS `video_favourites` (
  `fav_id` int(11) NOT NULL AUTO_INCREMENT,
  `fav_date` int(11) DEFAULT NULL,
  `user` int(11) DEFAULT NULL,
  `video_id` varchar(255) DEFAULT NULL,
  `timeline_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`fav_id`),
  KEY `video_id` (`video_id`)
) ENGINE=InnoDB  DEFAULT CHARSET=latin1 AUTO_INCREMENT=5 ;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `connections`
--
ALTER TABLE `connections`
  ADD CONSTRAINT `connections_ibfk_1` FOREIGN KEY (`user1`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `connections_ibfk_2` FOREIGN KEY (`user2`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`notification_receiver_id`) REFERENCES `notification_users` (`user_id`);

--
-- Constraints for table `timelines`
--
ALTER TABLE `timelines`
  ADD CONSTRAINT `timelines_ibfk_1` FOREIGN KEY (`connection_id`) REFERENCES `connections` (`connection_id`);

--
-- Constraints for table `videos`
--
ALTER TABLE `videos`
  ADD CONSTRAINT `videos_ibfk_1` FOREIGN KEY (`user`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `video_favourites`
--
ALTER TABLE `video_favourites`
  ADD CONSTRAINT `video_favourites_ibfk_1` FOREIGN KEY (`video_id`) REFERENCES `videos` (`video_id`);

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
