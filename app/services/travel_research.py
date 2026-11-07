"""Source-attested travel comparisons. No scraped/LLM values become facts implicitly."""

from datetime import date, datetime
from decimal import Decimal, ROUND_FLOOR
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Source(Record):
    publisher: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)
    data_date: date
    accessed_date: date
    evidence: str = Field(min_length=1, max_length=600)
    reviewed: bool = False

    @field_validator("url")
    @classmethod
    def public_reference(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Use an HTTPS source URL without credentials")
        if parsed.query or parsed.fragment:
            raise ValueError(
                "Use a public source URL without query tokens or fragments"
            )
        return value


class Quote(Record):
    kind: Literal["singapore_retail", "indicative", "estimate"]
    local_per_sgd: Decimal | None = Field(
        default=None, gt=0, le=1000000, max_digits=13, decimal_places=6
    )
    fee_sgd: Decimal = Field(
        default=Decimal("0"), ge=0, le=10000, max_digits=7, decimal_places=2
    )
    outlet: str = Field(default="", max_length=160)
    assumptions: str = Field(default="", max_length=600)
    source: Source | None = None


class Price(Record):
    amount: Decimal | None = Field(
        default=None, gt=0, le=100000000, max_digits=13, decimal_places=4
    )
    kind: Literal["observed", "estimate"] = "observed"
    source: Source | None = None


class Item(Record):
    label: str = Field(min_length=1, max_length=60)
    unit: str = Field(min_length=1, max_length=60)
    singapore: Price
    destination: Price
    comparability: str = Field(default="", max_length=400)


class Research(Record):
    schema_version: Literal[1] = 1
    country: str = Field(min_length=1, max_length=60)
    city: str = Field(min_length=1, max_length=60)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    budget_sgd: Decimal = Field(
        default=Decimal("50"), gt=0, le=10000, max_digits=7, decimal_places=2
    )
    retail_quote_required: bool = True
    quote: Quote
    items: list[Item] = Field(min_length=1, max_length=3)


def today() -> date:
    return datetime.now(ZoneInfo("Asia/Singapore")).date()


def template(country="Russia", city="Moscow", currency="RUB", budget="50") -> dict:
    return Research(
        country=country,
        city=city,
        currency=currency,
        budget_sgd=budget,
        quote=Quote(kind="singapore_retail"),
        items=[
            Item(
                label="Everyday item",
                unit="one item",
                singapore=Price(),
                destination=Price(),
            )
        ],
    ).model_dump(mode="json")


def digest(research: Research) -> str:
    return hashlib.sha256(research.model_dump_json().encode()).hexdigest()


def review_issues(research: Research, on: date | None = None) -> list[str]:
    on = on or today()
    issues = []
    quote = research.quote
    if quote.kind == "estimate":
        issues.append("An estimated exchange rate cannot support a factual video.")
    if research.retail_quote_required and quote.kind != "singapore_retail":
        issues.append(
            "A Singapore retail money-changer quotation is required; indicative rates are not a substitute."
        )
    if not quote.local_per_sgd:
        issues.append("Missing local currency received for one SGD.")
    if not quote.outlet or not quote.assumptions:
        issues.append(
            "Record the quoted outlet, sell-SGD direction, fees, minimum exchange and applicability to this budget."
        )
    if quote.fee_sgd >= research.budget_sgd:
        issues.append("Exchange fee must be below the budget.")

    def check_source(source, label, max_age):
        if not source:
            issues.append(f"{label}: missing source record.")
        else:
            if not source.reviewed:
                issues.append(f"{label}: source must be reviewed by a person.")
            if (
                source.data_date > on
                or source.accessed_date > on
                or source.accessed_date < source.data_date
            ):
                issues.append(f"{label}: invalid or future source dates.")
            if (on - source.data_date).days > max_age:
                issues.append(
                    f"{label}: source is stale (limit {max_age} days); obtain a current observation."
                )

    check_source(quote.source, "Exchange quotation", 7)
    for item in research.items:
        if not item.comparability:
            issues.append(
                f"{item.label}: explain sizes, shop/location, tax and whether the items are comparable."
            )
        for location, price in (
            ("Singapore", item.singapore),
            (research.city, item.destination),
        ):
            label = f"{item.label}, {location}"
            if not price.amount:
                issues.append(f"{label}: missing price.")
            if price.kind != "observed":
                issues.append(
                    f"{label}: estimate requires review and an observed replacement."
                )
            check_source(price.source, label, 30)
    return issues


def calculate(research: Research, on: date | None = None) -> list[dict]:
    issues = review_issues(research, on)
    if issues:
        raise ValueError("Research is incomplete: " + " ".join(issues))
    local_budget = (
        research.budget_sgd - research.quote.fee_sgd
    ) * research.quote.local_per_sgd
    return [
        {
            "label": item.label,
            "unit": item.unit,
            "sg_price": str(item.singapore.amount),
            "local_price": str(item.destination.amount),
            "sg_quantity": int(
                (research.budget_sgd / item.singapore.amount).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            ),
            "local_quantity": int(
                (local_budget / item.destination.amount).to_integral_value(
                    rounding=ROUND_FLOOR
                )
            ),
            "local_budget": str(local_budget),
        }
        for item in research.items
    ]


def storyline(research: Research) -> str:
    rows = calculate(research)
    parts = [
        f"What can {research.budget_sgd} Singapore dollars buy in Singapore versus {research.city}?",
        "Let's compare individual purchases, giving each item the full budget.",
    ]
    for row in rows:
        parts.append(
            f"For {row['label']}, the observed price per {row['unit']} is {row['sg_price']} Singapore dollars "
            f"versus {row['local_price']} {research.currency}. "
            f"That's {row['sg_quantity']} versus {row['local_quantity']} whole units."
        )
    kind = (
        "retail cash quotation"
        if research.quote.kind == "singapore_retail"
        else "indicative rate, not a retail offer"
    )
    parts.extend(
        [
            f"Our {kind} is dated {research.quote.source.data_date.isoformat()}; "
            f"exchange fees are {research.quote.fee_sgd} Singapore dollars.",
            "These are dated examples, not city averages. See the source record and exchange conditions before travelling.",
            "Where would you spend your fifty? Tell us your next comparison city."
            if research.budget_sgd == 50
            else "Where would you spend your budget? Tell us your next comparison city.",
        ]
    )
    return " ".join(parts)


def source_record(research: Research) -> bytes:
    return json.dumps(
        {
            "research": research.model_dump(mode="json"),
            "research_sha256": digest(research),
            "calculations": calculate(research),
            "narration": storyline(research),
            "method": "Each item uses the full budget independently; whole quantities are rounded down. Not a basket or a city index.",
        },
        ensure_ascii=False,
        indent=2,
    ).encode()
