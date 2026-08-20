"""Заказ покупателя и его движение по этапам.

Цепочка: заявка → согласование → счёт → чек об оплате → оплата подтверждена → поставка → завершено.
Покупатель двигает заказ, приложив чек; остальные переходы делает сотрудник.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from .catalog import MODELS, OPTIONS, PACKAGES, find
from .models import (AccountingItem, ConfigItem, Deal, DealStage, Delivery, Document, Payment,
                     TimelineEvent, Training, User)

# Этапы заказа. actor — кто двигает заказ дальше на этом этапе.
STAGES = [
    {'key': 'new', 'title': 'Заявка', 'actor': 'staff',
     'client': 'Заявка отправлена менеджеру, ожидайте согласования состава и цены.',
     'staff': 'Согласуйте с клиентом состав, цену и срок поставки.'},
    {'key': 'agreed', 'title': 'Согласовано', 'actor': 'staff',
     'client': 'Состав согласован. Менеджер готовит счёт.',
     'staff': 'Загрузите счёт-фактуру — заказ перейдёт дальше сам. Либо нажмите '
              '«Запросить оплату», если счёт отправлен клиенту другим способом.'},
    {'key': 'invoiced', 'title': 'Счёт выставлен', 'actor': 'client',
     'client': 'Оплатите счёт и приложите чек — заказ перейдёт на проверку оплаты.',
     'staff': 'У клиента запрошена оплата. Ждём чек.'},
    {'key': 'receipt', 'title': 'Чек приложен', 'actor': 'staff',
     'client': 'Чек на проверке у менеджера.',
     'staff': 'Проверьте чек и подтвердите оплату либо верните на доработку.'},
    {'key': 'paid', 'title': 'Оплата подтверждена', 'actor': 'staff',
     'client': 'Оплата принята, готовим отгрузку.',
     'staff': 'Подготовьте комплект и отправьте технику клиенту.'},
    {'key': 'shipped', 'title': 'Поставка', 'actor': 'staff',
     'client': 'Техника в пути. После вручения заказ будет закрыт.',
     'staff': 'Подтвердите вручение и закройте заказ.'},
    {'key': 'done', 'title': 'Завершено', 'actor': None,
     'client': 'Заказ закрыт. Документы остаются в кабинете.',
     'staff': 'Заказ закрыт.'},
]

STAGE_INDEX = {s['key']: i for i, s in enumerate(STAGES)}

# Кнопки сотрудника: этап → (подпись, следующий этап, запись в журнал)
STAFF_ACTIONS = {
    'new': ('Принять заявку', 'agreed', 'Заявка принята менеджером'),
    'agreed': ('Запросить оплату', 'invoiced', 'Счёт выставлен, у клиента запрошена оплата'),
    'receipt': ('Подтвердить оплату', 'paid', 'Оплата подтверждена по чеку клиента'),
    'paid': ('Отправить в поставку', 'shipped', 'Техника отгружена клиенту'),
    'shipped': ('Завершить заказ', 'done', 'Заказ закрыт: техника вручена клиенту'),
}

# Возврат на предыдущий этап, если что-то не так
STAFF_REJECTIONS = {
    'receipt': ('Вернуть на оплату', 'invoiced', 'Чек не принят, требуется повторная оплата'),
    'agreed': ('Вернуть в заявку', 'new', 'Согласование отменено, состав пересматривается'),
}


def stage_key(deal: Deal) -> str:
    position = max(0, min(deal.stage - 1, len(STAGES) - 1))
    return STAGES[position]['key']


def stage_info(deal: Deal) -> dict:
    """Этап заказа плюс его номер: «этап 2 из 7»."""
    index = STAGE_INDEX[stage_key(deal)]
    return {**STAGES[index], 'number': index + 1, 'total': len(STAGES)}


def order_total(model: dict, package: dict, options: list[dict]) -> float:
    return model['price'] + package['extra'] + sum(o['price'] for o in options)


def _build_stages(db: Session, deal: Deal) -> None:
    for i, stage in enumerate(STAGES):
        db.add(DealStage(deal_id=deal.id, position=i, title=stage['title'],
                         note='Принята' if i == 0 else 'Ожидает',
                         status='current' if i == 0 else 'pending'))


def create_order(db: Session, user: User, model_key: str, package_key: str,
                 option_keys: list[str], city: str = '', comment: str = '') -> Deal:
    model = find(MODELS, model_key)
    package = find(PACKAGES, package_key)
    options = [o for o in OPTIONS if o['key'] in option_keys]

    deal = Deal(
        company_id=user.company_id,
        product=model['name'],
        package=package['name'],
        amount=order_total(model, package, options),
        stage=1,
        comment=comment.strip(),
        source='Заказ из кабинета',
        created_by_id=user.id,
    )
    db.add(deal)
    db.flush()
    deal.number = str(1000 + deal.id)

    _build_stages(db, deal)
    log(db, deal, 'Заявка оформлена в кабинете',
        f'{model["name"]}, пакет «{package["name"]}»'
        + (f', опции: {", ".join(o["name"] for o in options)}' if options else ''),
        status='current')

    db.add(ConfigItem(deal_id=deal.id, section='platform', title=model['name'],
                      note=f'Бак {model["tank"]} · рабочая ширина {model["width"]} · {model["shift"]}',
                      included=True))
    db.add(ConfigItem(deal_id=deal.id, section='scenario', title='Опрыскивание',
                      note=f'Бак {model["tank"]}', included=True))
    db.add(ConfigItem(deal_id=deal.id, section='spec', title=model['name'],
                      note=f'Пакет «{package["name"]}»', included=True))
    for opt in options:
        db.add(ConfigItem(deal_id=deal.id, section='equipment', title=opt['name'],
                          note=opt['note'], price=opt['price'], included=True))
        db.add(ConfigItem(deal_id=deal.id, section='spec', title=opt['name'],
                          note=opt['note'], included=True))

    db.add(Payment(deal_id=deal.id, share=100, amount=deal.amount,
                   due_label='после выставления счёта', status='Ожидает счёта', paid=False))
    db.add(Delivery(deal_id=deal.id, origin='Склад Самара',
                    destination=city.strip() or (user.company.city if user.company else 'уточняется'),
                    current_point='—', status='Ожидает отгрузки', progress=0,
                    departed_label='—', eta_label='уточняется'))
    db.add(Training(deal_id=deal.id, date_label='согласуется', participants=2, confirmed=False))
    db.add(AccountingItem(deal_id=deal.id, title='Постановка на учёт', status='Ожидает поставки',
                          date_label='—', note='Документы готовятся к передаче техники'))
    db.add(AccountingItem(deal_id=deal.id, title='Сопровождение ЭПР', status='Ожидает договора',
                          date_label='—', note='Заявка подаётся после подписания договора'))

    db.commit()
    return deal


def log(db: Session, deal: Deal, title: str, note: str = '', status: str = 'done') -> None:
    """Пишет событие в журнал заказа — его видят и покупатель, и сотрудник."""
    position = db.query(TimelineEvent).filter(TimelineEvent.deal_id == deal.id,
                                              TimelineEvent.kind == 'deal').count()
    db.add(TimelineEvent(deal_id=deal.id, position=position,
                         date_label=f'{datetime.now():%d.%m}', title=title, note=note,
                         kind='deal', status=status))


def move_to(db: Session, deal: Deal, target_key: str, title: str, note: str = '') -> None:
    """Переводит заказ на указанный этап и отмечает пройденные шаги."""
    position = STAGE_INDEX[target_key]
    for stage in deal.stages:
        if stage.position < position:
            stage.status = 'done'
            if stage.note in ('Ожидает', ''):
                stage.note = 'Выполнено'
        elif stage.position == position:
            stage.status = 'current'
            stage.note = 'Текущий этап'
            stage.date_label = f'{datetime.now():%d.%m.%Y}'
        else:
            stage.status = 'pending'
            stage.note = 'Ожидает'
    deal.stage = position + 1

    for event in deal.events:
        if event.kind == 'deal' and event.status == 'current':
            event.status = 'done'
    log(db, deal, title, note, status='current')

    _sync_side_effects(db, deal, target_key)
    db.commit()


def _sync_side_effects(db: Session, deal: Deal, target_key: str) -> None:
    """Держит оплату и поставку в согласии с этапом заказа."""
    payment = deal.payments[0] if deal.payments else None
    if payment:
        if target_key == 'invoiced':
            payment.status = 'Счёт выставлен, ожидает оплаты'
            payment.due_label = 'по счёту'
        elif target_key == 'receipt':
            payment.status = 'Чек на проверке'
        elif target_key in ('paid', 'shipped', 'done'):
            payment.status = 'Оплачено'
            payment.paid = True
        elif target_key in ('new', 'agreed'):
            payment.status = 'Ожидает счёта'
            payment.paid = False

    if deal.delivery:
        if target_key == 'shipped':
            deal.delivery.status = 'В пути'
            deal.delivery.progress = 50
            deal.delivery.departed_label = f'{datetime.now():%d.%m}'
        elif target_key == 'done':
            deal.delivery.status = 'Доставлено'
            deal.delivery.progress = 100
        elif target_key in ('paid',):
            deal.delivery.status = 'Готовится к отгрузке'
            deal.delivery.progress = 15


def attach_invoice(db: Session, deal: Deal, doc: Document) -> None:
    """Счёт от сотрудника: заказ уходит на этап оплаты."""
    if stage_key(deal) in ('new', 'agreed'):
        move_to(db, deal, 'invoiced', 'Счёт выставлен', f'Документ «{doc.title}» доступен клиенту')


def attach_receipt(db: Session, deal: Deal, doc: Document) -> None:
    """Чек от покупателя: заказ уходит на проверку оплаты."""
    if stage_key(deal) in ('invoiced', 'receipt'):
        move_to(db, deal, 'receipt', 'Клиент приложил чек об оплате', f'Документ «{doc.title}»')


def staff_action(deal: Deal) -> tuple[str, str, str] | None:
    action = STAFF_ACTIONS.get(stage_key(deal))
    return action if action else None


def staff_rejection(deal: Deal) -> tuple[str, str, str] | None:
    return STAFF_REJECTIONS.get(stage_key(deal))


def client_can_upload_receipt(deal: Deal) -> bool:
    return stage_key(deal) in ('invoiced', 'receipt')
