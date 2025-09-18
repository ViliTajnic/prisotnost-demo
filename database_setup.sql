-- Time Management App - Oracle 23ai Database Schema

-- Create sequence for auto-incrementing IDs
CREATE SEQUENCE user_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE department_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE time_entry_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE project_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE schedule_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE leave_request_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE geofence_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE audit_log_seq START WITH 1 INCREMENT BY 1;

-- Departments table
CREATE TABLE departments (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    description CLOB,
    manager_id NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE users (
    id NUMBER PRIMARY KEY,
    username VARCHAR2(80) UNIQUE NOT NULL,
    email VARCHAR2(120) UNIQUE NOT NULL,
    password_hash VARCHAR2(255),  -- Nullable for OAuth users
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    role VARCHAR2(20) DEFAULT 'employee',
    department_id NUMBER,
    is_active NUMBER(1) DEFAULT 1,
    hire_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- OAuth fields
    google_id VARCHAR2(100) UNIQUE,
    github_id VARCHAR2(100) UNIQUE,
    microsoft_id VARCHAR2(100) UNIQUE,
    auth_provider VARCHAR2(20) DEFAULT 'local',
    profile_picture VARCHAR2(500),
    email_verified NUMBER(1) DEFAULT 0,
    last_login TIMESTAMP,

    -- Email verification fields
    email_verification_token VARCHAR2(100),
    email_verification_expires TIMESTAMP,

    CONSTRAINT fk_users_department FOREIGN KEY (department_id) REFERENCES departments(id),
    CONSTRAINT chk_role CHECK (role IN ('admin', 'manager', 'employee', 'hr')),
    CONSTRAINT chk_auth_provider CHECK (auth_provider IN ('local', 'google', 'github', 'microsoft'))
);

-- Projects table
CREATE TABLE projects (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(200) NOT NULL,
    description CLOB,
    client_name VARCHAR2(200),
    project_code VARCHAR2(50) UNIQUE,
    hourly_rate NUMBER(10,2),
    is_billable NUMBER(1) DEFAULT 1,
    start_date DATE,
    end_date DATE,
    status VARCHAR2(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_project_status CHECK (status IN ('active', 'inactive', 'completed', 'cancelled'))
);

-- Time entries table
CREATE TABLE time_entries (
    id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    clock_in_time TIMESTAMP NOT NULL,
    clock_out_time TIMESTAMP,
    total_hours NUMBER(8,2),
    break_duration NUMBER(8,2) DEFAULT 0,
    project_id NUMBER,
    location_lat NUMBER(10,8),
    location_lon NUMBER(11,8),
    notes CLOB,
    is_overtime NUMBER(1) DEFAULT 0,
    status VARCHAR2(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_time_entries_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_time_entries_project FOREIGN KEY (project_id) REFERENCES projects(id),
    CONSTRAINT chk_time_entry_status CHECK (status IN ('active', 'approved', 'rejected', 'pending'))
);

-- Schedules table
CREATE TABLE schedules (
    id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    shift_type VARCHAR2(50),
    notes CLOB,
    is_recurring NUMBER(1) DEFAULT 0,
    recurrence_pattern VARCHAR2(50),
    status VARCHAR2(20) DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_schedules_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT chk_schedule_status CHECK (status IN ('scheduled', 'completed', 'cancelled', 'modified'))
);

-- Leave requests table
CREATE TABLE leave_requests (
    id NUMBER PRIMARY KEY,
    user_id NUMBER NOT NULL,
    leave_type VARCHAR2(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days NUMBER(8,2),
    reason CLOB,
    status VARCHAR2(20) DEFAULT 'pending',
    approved_by NUMBER,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_leave_requests_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_leave_requests_approver FOREIGN KEY (approved_by) REFERENCES users(id),
    CONSTRAINT chk_leave_status CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    CONSTRAINT chk_leave_type CHECK (leave_type IN ('vacation', 'sick', 'personal', 'maternity', 'paternity', 'bereavement', 'other'))
);

-- Geofences table
CREATE TABLE geofences (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    center_lat NUMBER(10,8) NOT NULL,
    center_lon NUMBER(11,8) NOT NULL,
    radius NUMBER(10,2) NOT NULL,
    is_active NUMBER(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id NUMBER PRIMARY KEY,
    user_id NUMBER,
    action VARCHAR2(100) NOT NULL,
    table_name VARCHAR2(50),
    record_id NUMBER,
    old_values CLOB,
    new_values CLOB,
    ip_address VARCHAR2(45),
    user_agent CLOB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create triggers for auto-increment
CREATE OR REPLACE TRIGGER users_trigger
    BEFORE INSERT ON users
    FOR EACH ROW
BEGIN
    :NEW.id := user_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER department_trigger
    BEFORE INSERT ON departments
    FOR EACH ROW
BEGIN
    :NEW.id := department_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER time_entry_trigger
    BEFORE INSERT ON time_entries
    FOR EACH ROW
BEGIN
    :NEW.id := time_entry_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER project_trigger
    BEFORE INSERT ON projects
    FOR EACH ROW
BEGIN
    :NEW.id := project_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER schedule_trigger
    BEFORE INSERT ON schedules
    FOR EACH ROW
BEGIN
    :NEW.id := schedule_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER leave_request_trigger
    BEFORE INSERT ON leave_requests
    FOR EACH ROW
BEGIN
    :NEW.id := leave_request_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER geofence_trigger
    BEFORE INSERT ON geofences
    FOR EACH ROW
BEGIN
    :NEW.id := geofence_seq.NEXTVAL;
END;
/

CREATE OR REPLACE TRIGGER audit_log_trigger
    BEFORE INSERT ON audit_logs
    FOR EACH ROW
BEGIN
    :NEW.id := audit_log_seq.NEXTVAL;
END;
/

-- Create indexes for better performance
CREATE INDEX idx_time_entries_user_id ON time_entries(user_id);
CREATE INDEX idx_time_entries_date ON time_entries(clock_in_time);
CREATE INDEX idx_schedules_user_id ON schedules(user_id);
CREATE INDEX idx_schedules_date ON schedules(start_time);
CREATE INDEX idx_leave_requests_user_id ON leave_requests(user_id);
CREATE INDEX idx_users_department ON users(department_id);
CREATE INDEX idx_users_role ON users(role);

-- Insert sample data
INSERT INTO departments (name, description) VALUES ('IT', 'Information Technology Department');
INSERT INTO departments (name, description) VALUES ('HR', 'Human Resources Department');
INSERT INTO departments (name, description) VALUES ('Finance', 'Finance Department');
INSERT INTO departments (name, description) VALUES ('Sales', 'Sales Department');

-- Sample admin user (password is 'admin123' hashed)
INSERT INTO users (username, email, password_hash, first_name, last_name, role, department_id, hire_date)
VALUES ('admin', 'admin@company.com', 'scrypt:32768:8:1$XYZ123$hash_here', 'System', 'Administrator', 'admin', 1, SYSDATE);

-- Sample projects
INSERT INTO projects (name, description, client_name, project_code, hourly_rate, is_billable, start_date, status)
VALUES ('Internal Development', 'Internal application development', 'Company Internal', 'INT-001', 75.00, 0, SYSDATE, 'active');

INSERT INTO projects (name, description, client_name, project_code, hourly_rate, is_billable, start_date, status)
VALUES ('Client Project Alpha', 'Client web application development', 'ABC Corp', 'CLI-001', 125.00, 1, SYSDATE, 'active');

-- Sample geofence
INSERT INTO geofences (name, center_lat, center_lon, radius, is_active)
VALUES ('Main Office', 40.7128, -74.0060, 100.0, 1);

COMMIT;