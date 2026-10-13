from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_number: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_category: Mapped[str] = mapped_column(String(100), nullable=False)
