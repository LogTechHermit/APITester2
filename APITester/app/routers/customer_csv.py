import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Customer
from app.schemas import CustomerCreate, CustomerUpdate

router = APIRouter(tags=["customer CSV"])
CSV_HEADERS = [
    "Action",
    "Customer Number",
    "Customer Name",
    "Customer Type",
    "Customer Category",
]
MAX_CSV_SIZE = 10 * 1024 * 1024


@router.post("/api/customers/import")
def import_customers_csv(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict[str, object]:
    contents = file.file.read(MAX_CSV_SIZE + 1)
    if len(contents) > MAX_CSV_SIZE:
        raise HTTPException(
            status_code=413,
            detail="CSV file must be 10 MB or smaller.",
        )
    try:
        decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must use UTF-8 encoding.",
        ) from exc

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or missing its header row.",
        )
    reader.fieldnames = [header.strip() for header in reader.fieldnames]
    if reader.fieldnames != CSV_HEADERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV headers must be: {', '.join(CSV_HEADERS)}.",
        )

    result_rows: list[dict[str, object]] = []
    for row_number, row in enumerate(reader, start=2):
        if row is None:
            continue

        action = (row.get("Action") or "").strip().casefold()
        customer_number = (row.get("Customer Number") or "").strip()
        result: dict[str, object] = {
            "row": row_number,
            "action": action.title() or "Unknown",
            "customer_number": customer_number,
        }

        if None in row:
            result.update(
                status="error",
                message="Row has more values than the header.",
            )
            result_rows.append(result)
            continue
        if all(value is None or not value.strip() for value in row.values()):
            continue

        try:
            if action == "create":
                payload = CustomerCreate(
                    customer_number=customer_number,
                    customer_name=(row.get("Customer Name") or "").strip(),
                    customer_type=(row.get("Customer Type") or "").strip(),
                    customer_category=(row.get("Customer Category") or "").strip(),
                )
                db.add(Customer(**payload.model_dump()))
                db.commit()
            elif action == "update":
                payload = CustomerUpdate(
                    customer_name=(row.get("Customer Name") or "").strip(),
                    customer_type=(row.get("Customer Type") or "").strip(),
                    customer_category=(row.get("Customer Category") or "").strip(),
                )
                record = db.get(Customer, customer_number)
                if record is None:
                    result.update(
                        status="error",
                        message="Customer does not exist; Update requires an existing customer.",
                    )
                    result_rows.append(result)
                    continue
                for field, value in payload.model_dump().items():
                    setattr(record, field, value)
                db.commit()
            elif action == "delete":
                if not customer_number:
                    result.update(
                        status="error",
                        message="Customer Number is required for Delete.",
                    )
                    result_rows.append(result)
                    continue
                record = db.get(Customer, customer_number)
                if record is None:
                    result.update(
                        status="error",
                        message="Customer does not exist; Delete requires an existing customer.",
                    )
                    result_rows.append(result)
                    continue
                db.delete(record)
                db.commit()
            else:
                result.update(
                    status="error",
                    message="Action must be Create, Update, or Delete.",
                )
                result_rows.append(result)
                continue
        except ValidationError as exc:
            db.rollback()
            messages = [
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                for error in exc.errors()
            ]
            result.update(status="error", message="; ".join(messages))
        except IntegrityError:
            db.rollback()
            result.update(
                status="error",
                message="Customer Number already exists.",
            )
        else:
            result["status"] = "success"
        result_rows.append(result)

    successes = sum(row["status"] == "success" for row in result_rows)
    failures = len(result_rows) - successes
    return {
        "total_rows": len(result_rows),
        "succeeded": successes,
        "failed": failures,
        "results": result_rows,
    }


#@router.get("/export", include_in_schema=False)
@router.get("/api/customers/export", include_in_schema=False)
def export_customers_csv(db: Session = Depends(get_db)) -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for customer in db.scalars(
        select(Customer).order_by(Customer.customer_number)
    ):
        writer.writerow(
            [
                "Create",
                customer.customer_number,
                customer.customer_name,
                customer.customer_type,
                customer.customer_category,
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="customers.csv"'},
    )
