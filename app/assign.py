"""Ответственный за заказ: назначается автоматически, клиенту не нужно никого искать.

Берём сотрудников продаж (менеджер, затем руководитель) и выбираем того, у кого меньше
всего незакрытых заказов. Если в продажах никого нет — руководство компании.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import COMPANY
from .models import ROLE_STAFF, Deal, StaffRole, User

# Кто принимает заказы — по порядку: первая группа, в которой есть сотрудники
OWNER_GROUPS = [('sales_manager', 'sales_head'), ('coo', 'ceo')]
DONE_STAGE = 7


def _open_deals(db: Session, email: str) -> int:
    return len([d for d in db.scalars(select(Deal).where(Deal.specialist_email == email))
                if d.stage < DONE_STAGE])


def pick_owner(db: Session) -> tuple[User, str] | None:
    """Сотрудник с наименьшей загрузкой и название его должности."""
    roles = {r.key: r.name for r in db.scalars(select(StaffRole))}
    for group in OWNER_GROUPS:
        staff = list(db.scalars(select(User).where(User.role == ROLE_STAFF, User.staff_role.in_(group))
                                .order_by(User.id)))
        if staff:
            owner = min(staff, key=lambda u: (_open_deals(db, u.email), group.index(u.staff_role)))
            return owner, roles.get(owner.staff_role, 'Менеджер продаж')
    return None


def ensure_owner(db: Session, deal: Deal) -> bool:
    """Назначает ответственного, если его ещё нет. Возвращает True, если назначили."""
    if deal.specialist_name:
        return False
    picked = pick_owner(db)
    if picked is None:
        deal.specialist_name = COMPANY.get('contact', '')
        deal.specialist_role = 'Менеджер продаж'
        deal.specialist_phone = COMPANY['phone']
        deal.specialist_email = COMPANY['email']
        return True
    owner, role_name = picked
    deal.specialist_name = owner.full_name
    deal.specialist_role = role_name
    # Если у сотрудника не указан телефон — клиент звонит на общий номер
    deal.specialist_phone = owner.phone or COMPANY['phone']
    deal.specialist_email = owner.email
    return True
