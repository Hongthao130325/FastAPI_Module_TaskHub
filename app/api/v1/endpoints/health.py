from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def check_api():
    return {"status": "healthy", "version": "v1"}
