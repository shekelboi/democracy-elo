import random
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST

Base = declarative_base()


class Country(Base):
    __tablename__ = "country"
    id: str = Column(Text, primary_key=True)
    name: str = Column(String)
    elo: float = Column(Float)


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


# Connect to SQLite
engine = create_engine("sqlite:///db/countries.sqlite", echo=False, connect_args={"timeout": 2})
Session = sessionmaker(bind=engine)
session = Session()

app = FastAPI()


# GET endpoint
@app.get("/countries")
def countries_endpoint():
    countries = session.query(Country).all()
    return [c for c in countries]


@app.get("/country")
def country_endpoint(id: str):
    country = session.query(Country).where(Country.id == id.upper()).one_or_none()
    if not country:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": "Country not found"}
        )
    return country


@app.get("/random_pair")
def random_pair_endpoint():
    countries = session.query(Country).all()
    country1, country2 = random.sample(countries, 2)
    return country1, country2


@app.api_route("/select_winner", methods=["POST", "GET"])
def select_winner_endpoint(country1_id, country2_id, winner: bool):
    """

    :param country1_id: First country in the race.
    :param country2_id: Second country in the race.
    :param winner: True if country1 is the winner, false if country2 is the winner.
    :return: Success or error.
    """
    country1_id, country2_id = country1_id.upper(), country2_id.upper()
    country1 = session.query(Country).where(Country.id == country1_id).with_for_update().one_or_none()
    country2 = session.query(Country).where(Country.id == country2_id).with_for_update().one_or_none()
    if not country1 or not country2:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"error": "Country not found"}
        )
    change = calculate_elo(country1.elo, country2.elo, winner)

    result = round(calculate_elo(country1.elo, country2.elo, winner), 4)
    country1.elo += result
    country2.elo -= result
    session.commit()
    return {"change": change}
