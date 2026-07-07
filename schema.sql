-- MySQL Database Schema for Student Management System
-- Compatible with local deployments and Amazon RDS MySQL

-- Create Database if not exists
CREATE DATABASE IF NOT EXISTS student_db;
USE student_db;

-- Create Students Table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    course VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create Users Table (Authentication)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified TINYINT DEFAULT 0,
    otp_code VARCHAR(6) DEFAULT NULL,
    otp_expiry TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert 5 Sample Student Records for Demonstration
INSERT INTO students (full_name, email, phone, course, department) VALUES
('John Doe', 'john.doe@example.com', '+1-555-0199', 'Computer Science', 'CSE'),
('Jane Smith', 'jane.smith@example.com', '+1-555-0188', 'Cyber Security', 'CSE Cyber Security'),
('Alex Johnson', 'alex.j@example.com', '+1-555-0177', 'Artificial Intelligence', 'AI & ML'),
('Sarah Lee', 'sarah.lee@example.com', '+1-555-0166', 'Computer Science', 'CSE'),
('Michael Brown', 'michael.b@example.com', '+1-555-0155', 'Artificial Intelligence', 'AI & ML')
ON DUPLICATE KEY UPDATE 
    full_name = VALUES(full_name),
    phone = VALUES(phone),
    course = VALUES(course),
    department = VALUES(department);
