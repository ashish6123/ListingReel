from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user
from app.limiter import limiter
from app.models.schemas import GenerateScriptRequest, GenerateScriptResponse
from app.services.llm import LLMError, generate_script

router = APIRouter(prefix="/api", tags=["script"])


@router.post("/generate-script", response_model=GenerateScriptResponse)
@limiter.limit("20/minute")
async def generate_script_route(
    request: Request,
    payload: GenerateScriptRequest,
    user_id: str = Depends(get_current_user),
) -> GenerateScriptResponse:
    try:
        script = await generate_script(
            address=payload.address,
            price=payload.price,
            beds=payload.beds,
            baths=payload.baths,
            sqft=payload.sqft,
            description=payload.description,
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate script: {exc}",
        ) from exc

    return GenerateScriptResponse(script=script)
