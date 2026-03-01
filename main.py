from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

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
engine = create_engine("sqlite:///db/countries.sqlite", echo=False)
Session = sessionmaker(bind=engine)
session = Session()

# Query all countries
countries = session.query(Country).all()
for c in countries:
    print(c.id, c.name, round(c.elo, 4))
