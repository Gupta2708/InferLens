from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.schemas.providers import ProviderListOut, ProviderModelOut
from app.services.provider_catalog import effective_mock_mode, load_provider_rows

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _models_from_db(db: Session) -> list[ProviderModelOut]:
    return [
        ProviderModelOut(
            provider=row["provider"],
            model=row["model"],
            enabled=row["enabled"],
            key_configured=row["key_configured"],
            available=row["available"],
            status_label=row["status_label"],
            supports_streaming=row["supports_streaming"],
            input_cost_per_1k_tokens=row["input_cost_per_1k_tokens"],
            output_cost_per_1k_tokens=row["output_cost_per_1k_tokens"],
        )
        for row in load_provider_rows(db)
    ]


@router.get("", response_model=ProviderListOut)
def list_providers(db: Session = Depends(get_db)):
    models = _models_from_db(db)
    return ProviderListOut(
        providers=sorted({item.provider for item in models}),
        models=models,
        mock_mode=effective_mock_mode(get_settings()),
    )


@router.get("/models", response_model=list[ProviderModelOut])
def list_models(db: Session = Depends(get_db)):
    return _models_from_db(db)
