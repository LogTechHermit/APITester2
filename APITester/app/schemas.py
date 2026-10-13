from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    customer_number: str = Field(min_length=1, max_length=50)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_type: str = Field(min_length=1, max_length=100)
    customer_category: str = Field(min_length=1, max_length=100)


class CustomerUpdate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    customer_type: str = Field(min_length=1, max_length=100)
    customer_category: str = Field(min_length=1, max_length=100)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_number: str
    customer_name: str
    customer_type: str
    customer_category: str
