from sqlalchemy.orm import Session, selectinload

from ..models import ConversionTable


def get_active_conversion_table(
    db: Session,
    max_primary: int,
) -> ConversionTable | None:
    """
    Ищет активную таблицу перевода, у которой max_primary совпадает
    с максимальным первичным баллом варианта.
    Если активных таблиц несколько - берём самую свежую (больший id).
    Если таблицы нет - возвращаем None, и вторичный балл останется пустым.
    """
    return (
        db.query(ConversionTable)
        .options(selectinload(ConversionTable.entries))
        .filter(
            ConversionTable.is_active.is_(True),
            ConversionTable.max_primary == max_primary,
        )
        .order_by(ConversionTable.id.desc())
        .first()
    )
