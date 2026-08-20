from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Роли входа: покупатель (клиент), поставщик (дилер), сотрудник
ROLE_CLIENT = 'client'
ROLE_DEALER = 'dealer'
ROLE_STAFF = 'staff'

ROLE_TITLES = {
    ROLE_CLIENT: 'Кабинет клиента',
    ROLE_DEALER: 'Кабинет поставщика',
    ROLE_STAFF: 'Кабинет сотрудника',
}

ROLE_HOME = {
    ROLE_CLIENT: '/cabinet',
    ROLE_DEALER: '/dealer',
    ROLE_STAFF: '/staff',
}


class Company(Base):
    __tablename__ = 'companies'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    inn: Mapped[str] = mapped_column(String(16), default='')
    city: Mapped[str] = mapped_column(String(80), default='')
    kind: Mapped[str] = mapped_column(String(16), default=ROLE_CLIENT)
    dealer_level: Mapped[str] = mapped_column(String(16), default='Silver')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    users: Mapped[list['User']] = relationship(back_populates='company')
    deals: Mapped[list['Deal']] = relationship(back_populates='company')


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40), default='')
    role: Mapped[str] = mapped_column(String(16))
    staff_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    company: Mapped[Company | None] = relationship(back_populates='users')

    @property
    def role_title(self) -> str:
        return ROLE_TITLES.get(self.role, '')

    @property
    def home_url(self) -> str:
        return ROLE_HOME.get(self.role, '/')


class Deal(Base):
    __tablename__ = 'deals'

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'))
    number: Mapped[str] = mapped_column(String(32), default='')
    product: Mapped[str] = mapped_column(String(80), default='DJI T100')
    package: Mapped[str] = mapped_column(String(80), default='Профессиональная')
    amount: Mapped[float] = mapped_column(Float, default=0)
    stage: Mapped[int] = mapped_column(Integer, default=1)
    specialist_name: Mapped[str] = mapped_column(String(120), default='')
    specialist_role: Mapped[str] = mapped_column(String(120), default='Инженер внедрения')
    specialist_phone: Mapped[str] = mapped_column(String(40), default='')
    specialist_email: Mapped[str] = mapped_column(String(120), default='')
    # Заказ, оформленный покупателем из кабинета
    comment: Mapped[str] = mapped_column(Text, default='')
    source: Mapped[str] = mapped_column(String(40), default='Менеджер')
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    company: Mapped[Company] = relationship(back_populates='deals')
    created_by: Mapped['User | None'] = relationship(foreign_keys=[created_by_id])
    stages: Mapped[list['DealStage']] = relationship(back_populates='deal', order_by='DealStage.position')
    events: Mapped[list['TimelineEvent']] = relationship(back_populates='deal', order_by='TimelineEvent.position')
    documents: Mapped[list['Document']] = relationship(back_populates='deal', order_by='Document.id')
    payments: Mapped[list['Payment']] = relationship(back_populates='deal', order_by='Payment.id')
    delivery: Mapped['Delivery'] = relationship(back_populates='deal', uselist=False)
    config_items: Mapped[list['ConfigItem']] = relationship(back_populates='deal', order_by='ConfigItem.id')
    training: Mapped['Training'] = relationship(back_populates='deal', uselist=False)
    operations: Mapped[list['Operation']] = relationship(back_populates='deal', order_by='Operation.id')
    tickets: Mapped[list['ServiceTicket']] = relationship(back_populates='deal', order_by='ServiceTicket.id')
    accounting: Mapped[list['AccountingItem']] = relationship(back_populates='deal', order_by='AccountingItem.id')

    @property
    def current_stage(self) -> 'DealStage | None':
        current = [s for s in self.stages if s.status == 'current']
        if current:
            return current[0]
        return self.stages[-1] if self.stages else None

    @property
    def status_label(self) -> str:
        stage = self.current_stage
        return stage.title if stage else 'Без стадии'

    @property
    def files(self) -> list['Document']:
        return [d for d in self.documents if d.stored_name]


class DealStage(Base):
    """Шаг конвейера заказа. Состав этапов задаётся в orders.STAGES."""

    __tablename__ = 'deal_stages'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(60))
    date_label: Mapped[str] = mapped_column(String(40), default='')
    note: Mapped[str] = mapped_column(String(80), default='')
    status: Mapped[str] = mapped_column(String(16), default='pending')  # done / current / pending

    deal: Mapped[Deal] = relationship(back_populates='stages')


class TimelineEvent(Base):
    """Журнал событий сделки и поставки."""

    __tablename__ = 'timeline_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    position: Mapped[int] = mapped_column(Integer, default=0)
    date_label: Mapped[str] = mapped_column(String(40), default='')
    title: Mapped[str] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(Text, default='')
    kind: Mapped[str] = mapped_column(String(16), default='deal')  # deal / delivery
    status: Mapped[str] = mapped_column(String(16), default='done')

    deal: Mapped[Deal] = relationship(back_populates='events')


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    title: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(40), default='PDF')
    status: Mapped[str] = mapped_column(String(60), default='')
    status_tone: Mapped[str] = mapped_column(String(16), default='ok')  # ok / warn / blue / dim
    size_label: Mapped[str] = mapped_column(String(24), default='')
    date_label: Mapped[str] = mapped_column(String(24), default='')
    # invoice — счёт от сотрудника, receipt — чек от покупателя, other — прочее
    doc_type: Mapped[str] = mapped_column(String(16), default='other')
    # Загруженный файл: пустые поля означают запись-заглушку без вложения
    file_name: Mapped[str] = mapped_column(String(255), default='')
    stored_name: Mapped[str] = mapped_column(String(255), default='')
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    visible_to_client: Mapped[bool] = mapped_column(Boolean, default=True)

    deal: Mapped[Deal] = relationship(back_populates='documents')
    uploaded_by: Mapped['User | None'] = relationship(foreign_keys=[uploaded_by_id])

    @property
    def has_file(self) -> bool:
        return bool(self.stored_name)

    @property
    def type_label(self) -> str:
        return {'invoice': 'Счёт-фактура', 'receipt': 'Чек об оплате'}.get(self.doc_type, 'Документ')


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    share: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[float] = mapped_column(Float, default=0)
    due_label: Mapped[str] = mapped_column(String(40), default='')
    status: Mapped[str] = mapped_column(String(40), default='Ожидает оплаты')
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    deal: Mapped[Deal] = relationship(back_populates='payments')


class Delivery(Base):
    __tablename__ = 'deliveries'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    origin: Mapped[str] = mapped_column(String(80), default='Владивосток')
    destination: Mapped[str] = mapped_column(String(80), default='Самара')
    current_point: Mapped[str] = mapped_column(String(80), default='')
    status: Mapped[str] = mapped_column(String(40), default='В пути')
    progress: Mapped[int] = mapped_column(Integer, default=0)
    departed_label: Mapped[str] = mapped_column(String(24), default='')
    eta_label: Mapped[str] = mapped_column(String(24), default='')

    deal: Mapped[Deal] = relationship(back_populates='delivery')


class ConfigItem(Base):
    """Позиция комплектации: платформа, сценарий, оснащение, спецификация."""

    __tablename__ = 'config_items'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    section: Mapped[str] = mapped_column(String(24))  # platform / scenario / equipment / spec
    title: Mapped[str] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(String(200), default='')
    price: Mapped[float] = mapped_column(Float, default=0)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    included: Mapped[bool] = mapped_column(Boolean, default=False)

    deal: Mapped[Deal] = relationship(back_populates='config_items')


class Training(Base):
    __tablename__ = 'trainings'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    date_label: Mapped[str] = mapped_column(String(60), default='25–26 сентября')
    participants: Mapped[int] = mapped_column(Integer, default=2)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deal: Mapped[Deal] = relationship(back_populates='training')


class AccountingItem(Base):
    """Учёт и ЭПР."""

    __tablename__ = 'accounting_items'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default='')
    date_label: Mapped[str] = mapped_column(String(24), default='')
    note: Mapped[str] = mapped_column(String(200), default='')

    deal: Mapped[Deal] = relationship(back_populates='accounting')


class Operation(Base):
    """История обработок полей."""

    __tablename__ = 'operations'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    date_label: Mapped[str] = mapped_column(String(24))
    field: Mapped[str] = mapped_column(String(60))
    crop: Mapped[str] = mapped_column(String(60))
    scenario: Mapped[str] = mapped_column(String(60))
    area: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(16), default='га')
    status: Mapped[str] = mapped_column(String(24), default='Завершено')
    planned: Mapped[bool] = mapped_column(Boolean, default=False)

    deal: Mapped[Deal] = relationship(back_populates='operations')


class ServiceTicket(Base):
    __tablename__ = 'service_tickets'

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'))
    number: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default='В работе')
    date_label: Mapped[str] = mapped_column(String(24), default='')
    note: Mapped[str] = mapped_column(String(200), default='')

    deal: Mapped[Deal] = relationship(back_populates='tickets')


class Part(Base):
    """Запчасть каталога: артикул, цена, наличие, узел и совместимость."""

    __tablename__ = 'parts'

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    article: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(300))
    price: Mapped[float] = mapped_column(Float, default=0)
    stock: Mapped[str] = mapped_column(String(32), default='Под заказ')
    group: Mapped[str] = mapped_column(String(80), index=True, default='Прочие узлы')
    kind: Mapped[str] = mapped_column(String(80), index=True, default='Прочее')
    models: Mapped[str] = mapped_column(String(160), default='')  # «T50,T40,T25»
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def model_list(self) -> list[str]:
        return [m for m in self.models.split(',') if m]

    @property
    def in_stock(self) -> bool:
        return self.stock.lower() not in ('под заказ', 'нет', 'снят с продажи', '')


class PartRequestItem(Base):
    """Позиция в запросе КП на запчасти."""

    __tablename__ = 'part_request_items'

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey('requests.id'))
    part_id: Mapped[int] = mapped_column(ForeignKey('parts.id'))
    qty: Mapped[int] = mapped_column(Integer, default=1)

    part: Mapped[Part] = relationship()


class Lead(Base):
    """Клиент дилера."""

    __tablename__ = 'leads'

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'))
    name: Mapped[str] = mapped_column(String(160))
    stage: Mapped[str] = mapped_column(String(60), default='Новый лид')
    contact: Mapped[str] = mapped_column(String(120), default='')
    note: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DealerOrder(Base):
    """Оптовая заявка дилера."""

    __tablename__ = 'dealer_orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'))
    model: Mapped[str] = mapped_column(String(60))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(60), default='Новая заявка')
    comment: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Request(Base):
    """Заявка с публичной формы «Получить КП» и обращения из кабинетов."""

    __tablename__ = 'requests'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40), default='')
    email: Mapped[str] = mapped_column(String(120), default='')
    farm: Mapped[str] = mapped_column(String(160), default='')
    area: Mapped[str] = mapped_column(String(40), default='')
    comment: Mapped[str] = mapped_column(Text, default='')
    source: Mapped[str] = mapped_column(String(40), default='Форма КП')
    status: Mapped[str] = mapped_column(String(40), default='Новая')
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RoiCalculation(Base):
    """Сохранённый расчёт ROI-калькулятора."""

    __tablename__ = 'roi_calculations'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    mode: Mapped[str] = mapped_column(String(24), default='own')
    area: Mapped[float] = mapped_column(Float, default=0)
    crops: Mapped[str] = mapped_column(String(120), default='')
    passes: Mapped[int] = mapped_column(Integer, default=0)
    price_per_ha: Mapped[float] = mapped_column(Float, default=0)
    season_days: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_ha: Mapped[float] = mapped_column(Float, default=0)
    season_saving: Mapped[float] = mapped_column(Float, default=0)
    payback_months: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ===== Справочник должностей сотрудников =====

class StaffRole(Base):
    __tablename__ = 'staff_roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    dept: Mapped[int] = mapped_column(Integer, default=1)
    dept_tag: Mapped[str] = mapped_column(String(120), default='')
    status: Mapped[str] = mapped_column(String(16), default='review')  # review / draft
    approver: Mapped[str] = mapped_column(Text, default='')
    open_questions: Mapped[str] = mapped_column(Text, default='')
    pipeline_highlight: Mapped[str] = mapped_column(String(60), default='')  # "1,6"
    position: Mapped[int] = mapped_column(Integer, default=0)

    kpis: Mapped[list['StaffKpi']] = relationship(back_populates='role', order_by='StaffKpi.id')
    processes: Mapped[list['StaffProcess']] = relationship(back_populates='role', order_by='StaffProcess.id')
    rules: Mapped[list['StaffRule']] = relationship(back_populates='role', order_by='StaffRule.id')
    tasks: Mapped[list['StaffTask']] = relationship(back_populates='role', order_by='StaffTask.id')

    @property
    def highlight(self) -> list[int]:
        if not self.pipeline_highlight:
            return []
        return [int(x) for x in self.pipeline_highlight.split(',') if x.strip()]


class StaffKpi(Base):
    __tablename__ = 'staff_kpis'

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('staff_roles.id'))
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(String(80))
    red_line: Mapped[str] = mapped_column(String(80), default='')

    role: Mapped[StaffRole] = relationship(back_populates='kpis')


class StaffProcess(Base):
    __tablename__ = 'staff_processes'

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('staff_roles.id'))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    result: Mapped[str] = mapped_column(String(200))
    kpi: Mapped[str] = mapped_column(String(200))

    role: Mapped[StaffRole] = relationship(back_populates='processes')


class StaffRule(Base):
    __tablename__ = 'staff_rules'

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('staff_roles.id'))
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16), default='rule')  # rule / forbidden / audit

    role: Mapped[StaffRole] = relationship(back_populates='rules')


class StaffTask(Base):
    __tablename__ = 'staff_tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('staff_roles.id'))
    date_label: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(Text, default='')

    role: Mapped[StaffRole] = relationship(back_populates='tasks')
