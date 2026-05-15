
from mcp.server.fastmcp import FastMCP
import datetime

mcp = FastMCP("tp-mcp-demo")

@mcp.tool()
def calculate_rental_price(start_date: str, end_date: str, driver_age: int) -> dict:
    """
    Calculate the rental price for a car rental.

    Rules:
    - The rental price is calculated based on the start and end dates of the rental, the driver's age,
    and the type of car.

    - une voiture est louée entre une date de début et une date de fin ;
    - tout jour commencé est facturé ;
    - tarif de base par jour ;
    - assurance par jour ;
    - supplément jeune conducteur si l'âge du conducteur est inférieur à 25 ans ;
    - frais de dossier fixes ;
    - remise de 10 % si la location dure au moins 5 jours commencés.
    """
    if start_date > end_date:
        return {
            "error": "start_date_after_end_date",
            "message": "The start date cannot be after the end date."
        }
    # Conversion des dates en datetime
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    # Calcul du nombre de jours de location
    days = (end_date - start_date).days
    # Tarif de base par jour
    base_price = days * 50
    # Remise de 10 % si la location dure au moins 5 jours commencés.
    if days >= 5:
        base_price *= 0.9

    if driver_age < 25:
        base_price += days * 10

    base_price += 100

    return {
        "rental_price": base_price
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")
