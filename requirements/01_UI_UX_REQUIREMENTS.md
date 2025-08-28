# UI/UX Requirements

## 1. Overview
The AI Resume Review Platform provides a minimalist, desktop-focused web interface for recruitment consultants to upload and analyze candidate resumes using AI agents. The design emphasizes simplicity and efficiency with a modern, blue-based color scheme.

### Design Principles
- **Modern and minimal**: Clean interface with focus on functionality
- **Blue color scheme**: Professional blue-based branding
- **Desktop-first**: Optimized for desktop use (MVP)
- **Text-focused results**: Simple text display without charts/graphs

## 2. User Flows

### 2.1 Consultant Flow
1. **Login** → Enter credentials
2. **Home (Upload)** → Select industry, upload resume, enter candidate name
3. **View Results** → See AI analysis on same page after processing
4. **Download** → Export results as PDF or plain text
5. **History** → Access past analyses

### 2.2 Admin Flow
1. **Login** → Enter admin credentials
2. **Same as Consultant** → Full consultant capabilities
3. **User Management** → Add/remove consultant users

## 3. Screen Specifications

### 3.1 Login Page
- **Purpose**: Authenticate users
- **Elements**:
  - Company logo/name
  - Email input field
  - Password input field
  - "Login" button
  - Error message area
- **No registration link** (admin-only user creation)

### 3.2 Upload Resume Page (Home)
- **Purpose**: Primary workspace for resume analysis
- **Layout**: Sidebar navigation + main content area
- **Elements**:
  - **Upload Section**:
    - Candidate name input
    - Industry dropdown (6 options)
    - File upload button (PDF/DOCX)
    - "Analyze Resume" button
  - **Results Section** (appears after analysis):
    - Structure Agent results (text)
    - Appeal Point Agent results (text)
    - Download buttons (PDF, Plain Text)
  - **Processing State**:
    - Simple spinner with "Processing..." message

### 3.3 Review History Page
- **Purpose**: Access past analyses
- **Elements**:
  - Table/list of past analyses:
    - Date/time
    - Candidate name
    - Target industry
    - Status
    - "View" action button
  - Pagination or scroll for many results
  - Basic filtering by date range (future enhancement)

### 3.4 User Management Page (Admin only)
- **Purpose**: Manage consultant accounts
- **Elements**:
  - User list table:
    - Name
    - Email
    - Created date
    - "Remove" action
  - "Add New User" section:
    - Name input
    - Email input
    - Password input
    - "Create User" button

### 3.5 Common Elements
- **Sidebar Navigation**:
  - Company logo
  - Upload Resume (Home)
  - Review History
  - User Management (admin only)
  - User name/email
  - Logout button
- **Color**: Blue-based theme throughout

## 4. Input Validations

### 4.1 Login Form
- Email: Valid email format required
- Password: Required field

### 4.2 Upload Form
- Candidate Name: Required, min 2 characters
- Industry: Required selection
- File: Required, PDF or DOCX only, max 10MB

### 4.3 User Management
- Name: Required, min 2 characters
- Email: Required, valid format, unique
- Password: Required, no minimum length (MVP)

## 5. Error States and Messages

### 5.1 Login Errors
- "Invalid email or password"
- "Account has been deactivated"

### 5.2 Upload Errors
- "Please fill all required fields"
- "File must be PDF or DOCX format"
- "File size must be under 10MB"
- "Analysis failed. Please try again"

### 5.3 General Errors
- "Connection error. Please check your internet"
- "Session expired. Please login again"

## 6. Responsive Design Requirements
- **Desktop-only for MVP**
- Minimum viewport: 1024px width
- Fixed sidebar: 250px width
- Main content: Fluid width with max 1200px