import os
from sqlalchemy import (
    CheckConstraint,
    create_engine,
    Column,
    String,
    Numeric,
    Integer,
    Boolean,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Get DB connection string from environment variable (set in docker-compose.yml)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/solvency_db"
)

# Define the base class for declarative class definitions
Base = declarative_base()


# --- 1. Define the Client Table Model ---
class Client(Base):
    """
    SQLAlchemy model for the Client data, aggregating Identity, Financials,
    and Credit History as per the project requirements.
    """

    __tablename__ = "clients"

    # Identity Data (from ClientDirectoryService)
    client_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)

    # Financial Data (from FinancialDataService)
    # Using Numeric/Decimal for money to prevent floating point issues
    monthly_income = Column(Numeric(10, 2), nullable=False, default=0.00)
    monthly_expenses = Column(Numeric(10, 2), nullable=False, default=0.00)

    # Credit History (from CreditBureauService)
    debt = Column(Numeric(10, 2), nullable=False, default=0.00)
    # late_payments maps to nonNegativeInteger (Integer >= 0)
    late_payments = Column(Integer, nullable=False, default=0)
    has_bankruptcy = Column(Boolean, nullable=False, default=False)

    # Ensure income, expenses, debt are non-negative (Database-level validation)
    __table_args__ = (
        # Ensure income, expenses, debt, and late_payments are non-negative
        CheckConstraint("monthly_income >= 0", name="check_income_non_negative"),
        CheckConstraint("monthly_expenses >= 0", name="check_expenses_non_negative"),
        CheckConstraint("debt >= 0", name="check_debt_non_negative"),
        CheckConstraint("late_payments >= 0", name="check_late_payments_non_negative"),
    )

    def __repr__(self):
        return (
            f"Client(id='{self.client_id}', name='{self.name}', "
            f"income={self.monthly_income}, debt={self.debt})"
        )


# --- 2. Database Connection and Setup ---
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    """Create all tables defined in Base."""
    try:
        # Drops and creates tables. Use Base.metadata.create_all(engine) for production.
        # We use drop_all for easy testing reset.
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        print("Database tables created successfully.")
    except SQLAlchemyError as e:
        print(f"Error creating database tables: {e}")


# --- 3. Function to Insert Test Data ---
TEST_DATA = [
    # clientId      name            address         income expenses debt   late bankruptcy
    ("client-001", "John Doe", "123 Main St", 4000, 3000, 5000, 2, False),
    ("client-002", "Alice Smith", "456 Elm St", 3000, 2500, 2000, 0, False),
    ("client-003", "Bob Johnson", "789 Oak St", 6000, 5500, 10000, 5, True),
]


def insert_test_data():
    """Insert the mandatory test data into the clients table."""
    db = SessionLocal()
    try:
        # Map the tuple data to Client model objects
        clients = [
            Client(
                client_id=d[0],
                name=d[1],
                address=d[2],
                monthly_income=d[3],
                monthly_expenses=d[4],
                debt=d[5],
                late_payments=d[6],
                has_bankruptcy=d[7],
            )
            for d in TEST_DATA
        ]

        # Insert or merge the data
        db.bulk_save_objects(clients)
        db.commit()
        print(f"Successfully inserted {len(clients)} test clients.")
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error inserting test data: {e}")
    finally:
        db.close()


# --- 4. Initialization Script ---
if __name__ == "__main__":
    # This block runs when the file is executed directly
    # (e.g., in a dedicated setup container or at application startup)
    create_db_and_tables()
    insert_test_data()
