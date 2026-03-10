import os
import random

from sqlalchemy import create_engine, Column, String, Float, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST
from dotenv import load_dotenv

load_dotenv()
Base = declarative_base()

ALLOWED_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "").split(",")


class Country(Base):
    __tablename__ = "country"
    id: str = Column(Text, primary_key=True)
    name: str = Column(String)
    elo: float = Column(Float)

    def __hash__(self):
        return int("".join(map(str, map(ord, self.id))))


class Match(Base):
    __tablename__ = "match"
    id: str = Column(Integer, primary_key=True, autoincrement=True)
    ip: str = Column(String)
    countries: str = Column(String)
    winner: str = Column(String)


engine = create_engine("sqlite:///db/countries.sqlite", echo=False, connect_args={"timeout": 2})
SessionLocal = sessionmaker(bind=engine)
read_session = SessionLocal()

countries = read_session.query(Country).all()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_elo(country1: float, country2: float, winner: bool):
    """

    :param country1: ELO rating of the first country.
    :param country2: ELO rating of the second country.
    :param winner: True if the first country won, False if the second country won.
    :return: The change between the two countries' scores.
    The result has to be added to the first country and subtracted from the second.
    """
    winner = int(winner)
    diff = country2 - country1
    diff /= 400
    inverse_chance = 10 ** diff + 1
    # Chance of country1 winning
    expected_result = 1 / inverse_chance

    # Calculating the change in ELO rating
    k_factor = 20
    change = k_factor * (winner - expected_result)
    return change


def get_ip(request: Request):
    if os.environ.get("REVERSE_PROXY"):
        return request.headers.get("x-forwarded-for", request.client.host)
    return request.client.host


@app.get("/countries")
def countries_endpoint():
    countries = read_session.query(Country).all()
    return [c for c in countries]


@app.get("/country")
def country_endpoint(id: str):
    country = read_session.query(Country).where(Country.id == id.upper()).one_or_none()
    if not country:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": "Country not found"}
        )
    return country


@app.get("/random_pair")
def random_pair_endpoint():
    """
    Returns a random pair of countries in alphabetical order.
    :return: A random pair of countries.
    """
    country_pairs = {m.countries for m in read_session.query(Match).all()}

    limit = 1000

    for i in range(limit):
        country1, country2 = sorted(random.sample(countries, 2), key=lambda x: x.id)

        country_pair = f"{country1.id}-{country2.id}"
        if country_pair not in country_pairs:
            break

    # If we cannot find a unique pair, we just use the last pair we selected
    return country1, country2


@app.get("/my_votes")
def my_votes_endpoint(request: Request):
    """
    Returns all your votes.
    :return: All your previous votes.
    """
    votes = read_session.query(Match).filter(Match.ip == get_ip(request)).all()
    return votes


@app.api_route("/select_winner", methods=["POST", "GET"])
def select_winner_endpoint(request: Request, country1_id, country2_id, winner: bool):
    """
    :param country1_id: First country in the race.
    :param country2_id: Second country in the race.
    :param winner: True if country1 is the winner, false if country2 is the winner.
    :return: Success or error.
    """
    country1_id, country2_id = country1_id.upper(), country2_id.upper()
    country1_id, country2_id = sorted([country1_id, country2_id])  # Ensuring that they are in the right order
    if country1_id == country2_id:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": "Cannot compete a country against itself."}
        )

    with SessionLocal() as write_session:
        with write_session.begin():
            country1 = write_session.query(Country).where(
                Country.id == country1_id).one_or_none()
            country2 = write_session.query(Country).where(
                Country.id == country2_id).one_or_none()
            if not country1 or not country2:
                return JSONResponse(
                    status_code=HTTP_400_BAD_REQUEST,
                    content={"error": "Country not found"}
                )

            country_pair = f"{country1_id}-{country2_id}"
            match = write_session.query(Match).where(Match.ip == get_ip(request)).filter(
                Match.countries == country_pair).one_or_none()

            if match:
                # Silent refusal
                return {"change": 0}

            change = calculate_elo(country1.elo, country2.elo, winner)

            result = round(change, 4)
            country1.elo += result
            country2.elo -= result

            winner_country = country1_id if winner else country2_id

            write_session.add(Match(
                ip=request.client.host,
                countries=country_pair,
                winner=winner_country,
            ))

    return {"change": change}
