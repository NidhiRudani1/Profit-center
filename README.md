# Profit Centre

A Snowflake-native Profit Centre Management application built using **Streamlit** and **Snowpark for Python**. The application enables users to manage employees, Statements of Work (SOWs), resource allocation, and financial metrics including Revenue, Cost, Margin, and Profitability through an interactive dashboard.

---

## Features

### Employee Management
- Add, edit and delete employee records
- Maintain employee details including:
  - Employee ID
  - Name
  - Grade
  - Location
  - Country
  - Pillar
  - Start & End Dates
- Bulk employee upload using CSV
- Employee data export

---

### SOW (Statement of Work) Management

#### SOW Master
- Create and maintain SOW information
- Project assignment
- Contract value
- Start and End dates

#### SOW Details
- Assign employees to SOWs
- Configure:
  - Skill
  - Role
  - Billing Rate
  - Allocation Period
- Date range validation against SOW Master
- Bulk upload support
- Download SOW Details

---

### Dashboard

Interactive dashboard providing:

- Team List
- Resource Allocation
- Estimated Revenue
- Estimated Cost
- Margin
- Margin %
- Quarterly Summary
- Monthly Revenue
- Monthly Cost
- Revenue vs Cost Analysis
- Profitability Reports

---

### Financial Reporting

Automatically calculates:

- Monthly Revenue
- Monthly Cost
- Quarterly Revenue
- Quarterly Cost
- Quarterly Margin
- Margin Percentage
- Annual Summary

Supports Monthly Snapshot generation for comparison across reporting periods.

---

### Bulk Upload

Supports CSV uploads for:

- Employee Master
- SOW Master
- SOW Details

Validation includes:

- Required columns
- Duplicate records
- Employee existence
- SOW validation
- Date range validation

---

### Export

Download reports as CSV including:

- Employee List
- SOW Master
- SOW Details
- Dashboard Reports
- Financial Reports

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Snowflake | Data Warehouse |
| Snowpark Python | Database Operations |
| Streamlit | User Interface |
| Pandas | Data Processing |
| NumPy | Financial Calculations |
| SQL | Data Management |

---

## Database Objects

### Tables

- EMPLOYEE
- PILLAR
- PROJECT
- SOW_MASTER
- SOW_DETAILS
- ARC_COST_CARD
- MONTHLY_SNAPSHOT

---

## Functional Modules

```
Profit Centre
│
├── Employee
│   ├── Add Employee
│   ├── Edit Employee
│   ├── Delete Employee
│   ├── Bulk Upload
│   └── Download CSV
│
├── SOW
│   ├── SOW Master
│   ├── SOW Details
│   ├── Employee Assignment
│   ├── Validation
│   ├── Bulk Upload
│   └── Download CSV
│
└── Dashboard
    ├── Team List
    ├── Revenue
    ├── Cost
    ├── Margin
    ├── Margin %
    ├── Quarterly Summary
    └── Monthly Snapshot
```

---

## Key Validations

- Employee must exist before assigning to SOW
- SOW Detail dates must fall within SOW Master dates
- Duplicate employee assignments are prevented
- Required fields validation
- Bulk upload validation
- Data integrity checks

---

## Dashboard Metrics

The application computes:

- Estimated Monthly Revenue
- Estimated Monthly Cost
- Actual Revenue
- Actual Cost
- Quarterly Revenue
- Quarterly Cost
- Margin
- Margin %
- Annual Summary

---

## Future Enhancements

- Role-based access control
- Authentication
- Interactive charts and KPIs
- Forecasting using Snowflake Cortex AI
- Automated email reports
- Audit logging
- REST API integration
- Excel report generation

---

## Author

Developed as a Snowflake Streamlit Proof of Concept (POC) demonstrating Profit Centre Management, Resource Allocation, and Financial Analytics using Snowflake and Python.

---

## License

This project is intended for demonstration and learning purposes.
