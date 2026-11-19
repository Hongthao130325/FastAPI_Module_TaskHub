from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)


class PasswordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
