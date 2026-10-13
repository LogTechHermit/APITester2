from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)) -> list[Customer]:
    return list(db.scalars(select(Customer).order_by(Customer.customer_number)).all())


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate, db: Session = Depends(get_db)
) -> Customer:
    record = Customer(**customer.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this customer number already exists.",
        ) from exc
    db.refresh(record)
    return record


@router.post(
    "/bulk",
    response_model=list[CustomerRead],
    status_code=status.HTTP_201_CREATED,
)
def create_customers(
    customers: list[CustomerCreate], db: Session = Depends(get_db)
) -> list[Customer]:
    records = [Customer(**customer.model_dump()) for customer in customers]
    db.add_all(records)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A customer with this customer number already exists.",
        ) from exc
    for record in records:
        db.refresh(record)
    return records


@router.get("/{customer_number}", response_model=CustomerRead)
def get_customer(
    customer_number: str, db: Session = Depends(get_db)
) -> Customer:
    record = db.get(Customer, customer_number)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found."
        )
    return record


@router.put("/{customer_number}", response_model=CustomerRead)
def update_customer(
    customer_number: str,
    customer: CustomerUpdate,
    db: Session = Depends(get_db),
) -> Customer:
    record = db.get(Customer, customer_number)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found."
        )
    for field, value in customer.model_dump().items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{customer_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_number: str, db: Session = Depends(get_db)
) -> Response:
    record = db.get(Customer, customer_number)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found."
        )
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
