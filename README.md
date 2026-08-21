# Truck Tracking System

A real-time truck tracking and license plate recognition system developed for monitoring trucks entering and leaving a factory.

## Overview

The system uses an IP camera to monitor the factory entrance. Detected trucks are tracked in real time, their license plates are recognized, and the collected information is displayed on a web-based interface.

The system also includes user registration and login, database management, camera connection monitoring, email notifications, and truck record management.

## Features

- Real-time truck detection and tracking
- License plate recognition
- IP camera integration
- ROI (Region of Interest) selection
- Real-time camera connection status
- Web-based monitoring interface
- User registration and login
- SQLite database
- Password hashing
- Email notification when the camera connection is lost
- User-specific email notifications
- Truck record reset from the web interface
- Real-time communication between the image processing system and the web application

## System Flow

IP Camera
    ↓
Image Processing
    ↓
Truck Detection & Tracking
    ↓
License Plate Recognition
    ↓
FastAPI Backend
    ↓
Web Interface


## Screenshots

### Truck Tracking
<p align="center">
  <img width="1156" height="651" alt="truck_frame_1" src="https://github.com/user-attachments/assets/138aa79e-5357-4d28-91fc-b0ac5b9d1993" />
</p>
<p
<img width="989" height="647" alt="truck_frame_2" src="https://github.com/user-attachments/assets/bf60e499-b306-498d-8704-ecdfdc97b1b7" />
</p>

### Main Dashboard
<p align="center">
  <img width="1395" height="932" alt="main" src="https://github.com/user-attachments/assets/83f1e532-55f9-4d26-8761-189387ef064b" >
</p>

### Login Page
<p align="center">
   <img width="686" height="738" alt="image" src="https://github.com/user-attachments/assets/da60fb6d-304a-4a0f-aee5-aa0b2e832ea4" >
</p>
<p align="center">
<img width="707" height="887" alt="image" src="https://github.com/user-attachments/assets/b43ce950-df3e-4355-8515-625b5007ccc5" >
</p>
