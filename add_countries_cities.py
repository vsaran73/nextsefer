import os
import django
import csv
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextsefer.settings')
django.setup()

from sefer_app.models import Ulkeler, Sehirler

def add_countries():
    """Add Schengen countries plus Turkey, Romania, and Bulgaria to the database"""
    countries = [
        # Schengen countries
        {"ulke_adi": "Almanya", "ulke_kodu": "DE"},
        {"ulke_adi": "Avusturya", "ulke_kodu": "AT"},
        {"ulke_adi": "Belçika", "ulke_kodu": "BE"},
        {"ulke_adi": "Çek Cumhuriyeti", "ulke_kodu": "CZ"},
        {"ulke_adi": "Danimarka", "ulke_kodu": "DK"},
        {"ulke_adi": "Estonya", "ulke_kodu": "EE"},
        {"ulke_adi": "Finlandiya", "ulke_kodu": "FI"},
        {"ulke_adi": "Fransa", "ulke_kodu": "FR"},
        {"ulke_adi": "Hollanda", "ulke_kodu": "NL"},
        {"ulke_adi": "İspanya", "ulke_kodu": "ES"},
        {"ulke_adi": "İsveç", "ulke_kodu": "SE"},
        {"ulke_adi": "İsviçre", "ulke_kodu": "CH"},
        {"ulke_adi": "İtalya", "ulke_kodu": "IT"},
        {"ulke_adi": "İzlanda", "ulke_kodu": "IS"},
        {"ulke_adi": "Letonya", "ulke_kodu": "LV"},
        {"ulke_adi": "Liechtenstein", "ulke_kodu": "LI"},
        {"ulke_adi": "Litvanya", "ulke_kodu": "LT"},
        {"ulke_adi": "Lüksemburg", "ulke_kodu": "LU"},
        {"ulke_adi": "Macaristan", "ulke_kodu": "HU"},
        {"ulke_adi": "Malta", "ulke_kodu": "MT"},
        {"ulke_adi": "Norveç", "ulke_kodu": "NO"},
        {"ulke_adi": "Polonya", "ulke_kodu": "PL"},
        {"ulke_adi": "Portekiz", "ulke_kodu": "PT"},
        {"ulke_adi": "Slovakya", "ulke_kodu": "SK"},
        {"ulke_adi": "Slovenya", "ulke_kodu": "SI"},
        {"ulke_adi": "Yunanistan", "ulke_kodu": "GR"},
        {"ulke_adi": "Hırvatistan", "ulke_kodu": "HR"},
        {"ulke_adi": "Kıbrıs", "ulke_kodu": "CY"},
        {"ulke_adi": "Monaco", "ulke_kodu": "MC"},
        # Additional countries
        {"ulke_adi": "Türkiye", "ulke_kodu": "TR"},
        {"ulke_adi": "Romanya", "ulke_kodu": "RO"},
        {"ulke_adi": "Bulgaristan", "ulke_kodu": "BG"},
    ]

    countries_added = 0
    countries_exists = 0

    for country_data in countries:
        country, created = Ulkeler.objects.get_or_create(
            ulke_kodu=country_data["ulke_kodu"],
            defaults={"ulke_adi": country_data["ulke_adi"]}
        )
        
        if created:
            countries_added += 1
            print(f"Added country: {country.ulke_adi}")
        else:
            countries_exists += 1
            print(f"Country already exists: {country.ulke_adi}")

    print(f"\nTotal countries added: {countries_added}")
    print(f"Countries already in database: {countries_exists}")
    return countries_added, countries_exists

def add_cities():
    """Add major cities for each country in the database"""
    # Dictionary of country codes and their major cities
    cities_by_country = {
        "DE": ["Berlin", "Hamburg", "München", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf", "Leipzig", "Dortmund", "Essen", "Dresden", "Bremen"],
        "AT": ["Wien", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt", "Villach", "Wels", "Sankt Pölten", "Dornbirn"],
        "BE": ["Bruxelles", "Antwerpen", "Gent", "Charleroi", "Liège", "Brugge", "Namur", "Leuven", "Mons", "Aalst"],
        "CZ": ["Praha", "Brno", "Ostrava", "Plzeň", "Liberec", "Olomouc", "České Budějovice", "Hradec Králové", "Ústí nad Labem", "Pardubice"],
        "DK": ["København", "Aarhus", "Odense", "Aalborg", "Frederiksberg", "Esbjerg", "Randers", "Kolding", "Horsens", "Vejle"],
        "EE": ["Tallinn", "Tartu", "Narva", "Pärnu", "Kohtla-Järve", "Viljandi", "Rakvere", "Maardu", "Sillamäe", "Kuressaare"],
        "FI": ["Helsinki", "Espoo", "Tampere", "Vantaa", "Oulu", "Turku", "Jyväskylä", "Lahti", "Kuopio", "Pori"],
        "FR": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille"],
        "NL": ["Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Eindhoven", "Tilburg", "Groningen", "Almere", "Breda", "Nijmegen"],
        "ES": ["Madrid", "Barcelona", "Valencia", "Sevilla", "Zaragoza", "Málaga", "Murcia", "Palma", "Las Palmas", "Bilbao"],
        "SE": ["Stockholm", "Göteborg", "Malmö", "Uppsala", "Västerås", "Örebro", "Linköping", "Helsingborg", "Jönköping", "Norrköping"],
        "CH": ["Zürich", "Genève", "Basel", "Lausanne", "Bern", "Winterthur", "Luzern", "St. Gallen", "Lugano", "Biel/Bienne"],
        "IT": ["Roma", "Milano", "Napoli", "Torino", "Palermo", "Genova", "Bologna", "Firenze", "Bari", "Catania"],
        "IS": ["Reykjavík", "Kópavogur", "Hafnarfjörður", "Akureyri", "Reykjanesbær", "Garðabær", "Mosfellsbær", "Árborg", "Akranes", "Fjarðabyggð"],
        "LV": ["Riga", "Daugavpils", "Liepāja", "Jelgava", "Jūrmala", "Ventspils", "Rēzekne", "Valmiera", "Jēkabpils", "Ogre"],
        "LI": ["Vaduz", "Schaan", "Triesen", "Balzers", "Eschen", "Mauren", "Triesenberg", "Ruggell", "Gamprin", "Schellenberg"],
        "LT": ["Vilnius", "Kaunas", "Klaipėda", "Šiauliai", "Panevėžys", "Alytus", "Marijampolė", "Mažeikiai", "Jonava", "Utena"],
        "LU": ["Luxembourg", "Esch-sur-Alzette", "Differdange", "Dudelange", "Ettelbruck", "Diekirch", "Wiltz", "Echternach", "Rumelange", "Vianden"],
        "HU": ["Budapest", "Debrecen", "Szeged", "Miskolc", "Pécs", "Győr", "Nyíregyháza", "Kecskemét", "Székesfehérvár", "Szombathely"],
        "MT": ["Valletta", "Birkirkara", "Qormi", "Mosta", "Żabbar", "Sliema", "San Ġwann", "Naxxar", "Żejtun", "Rabat"],
        "NO": ["Oslo", "Bergen", "Trondheim", "Stavanger", "Drammen", "Fredrikstad", "Kristiansand", "Sandnes", "Tromsø", "Sarpsborg"],
        "PL": ["Warszawa", "Kraków", "Łódź", "Wrocław", "Poznań", "Gdańsk", "Szczecin", "Bydgoszcz", "Lublin", "Katowice"],
        "PT": ["Lisboa", "Porto", "Vila Nova de Gaia", "Amadora", "Braga", "Coimbra", "Funchal", "Setúbal", "Almada", "Agualva-Cacém"],
        "SK": ["Bratislava", "Košice", "Prešov", "Žilina", "Banská Bystrica", "Nitra", "Trnava", "Martin", "Trenčín", "Poprad"],
        "SI": ["Ljubljana", "Maribor", "Celje", "Kranj", "Koper", "Velenje", "Novo Mesto", "Ptuj", "Trbovlje", "Kamnik"],
        "GR": ["Athína", "Thessaloníki", "Pátra", "Irákleio", "Lárisa", "Vólos", "Ioánnina", "Chaniá", "Chalcída", "Kavála"],
        "HR": ["Zagreb", "Split", "Rijeka", "Osijek", "Zadar", "Pula", "Slavonski Brod", "Karlovac", "Varaždin", "Šibenik"],
        "CY": ["Nicosia", "Limassol", "Larnaca", "Paphos", "Strovolos", "Famagusta", "Kyrenia", "Morphou", "Athienou", "Aradippou"],
        "MC": ["Monaco", "Monte Carlo", "La Condamine", "Fontvieille", "Moneghetti", "Larvotto", "Saint Roman", "La Rousse", "La Colle", "Les Révoires"],
        "TR": ["İstanbul", "Ankara", "İzmir", "Bursa", "Adana", "Gaziantep", "Konya", "Antalya", "Kayseri", "Mersin", 
               "Eskişehir", "Diyarbakır", "Şanlıurfa", "Samsun", "Malatya", "Batman", "Trabzon", "Erzurum", "Van", "Edirne"],
        "RO": ["București", "Cluj-Napoca", "Timișoara", "Iași", "Constanța", "Craiova", "Brașov", "Galați", "Ploiești", "Oradea", 
               "Brăila", "Arad", "Pitești", "Sibiu", "Bacău", "Târgu Mureș", "Baia Mare", "Buzău", "Satu Mare", "Botoșani"],
        "BG": ["Sofia", "Plovdiv", "Varna", "Burgas", "Ruse", "Stara Zagora", "Pleven", "Sliven", "Dobrich", "Shumen", 
               "Pernik", "Haskovo", "Yambol", "Pazardzhik", "Blagoevgrad", "Veliko Tarnovo", "Vratsa", "Gabrovo", "Asenovgrad", "Vidin"],
    }

    cities_added = 0
    cities_exists = 0
    skipped_countries = []

    for country_code, cities in cities_by_country.items():
        try:
            country = Ulkeler.objects.get(ulke_kodu=country_code)
            for city_name in cities:
                city, created = Sehirler.objects.get_or_create(
                    ulke=country,
                    sehir_adi=city_name
                )
                
                if created:
                    cities_added += 1
                    print(f"Added city: {city.sehir_adi}, {country.ulke_adi}")
                else:
                    cities_exists += 1
                    print(f"City already exists: {city.sehir_adi}, {country.ulke_adi}")
        except Ulkeler.DoesNotExist:
            skipped_countries.append(country_code)
            print(f"Country with code {country_code} not found, skipping cities")

    print(f"\nTotal cities added: {cities_added}")
    print(f"Cities already in database: {cities_exists}")
    if skipped_countries:
        print(f"Skipped countries (not found): {', '.join(skipped_countries)}")
    return cities_added, cities_exists

if __name__ == "__main__":
    print("Starting to add countries and cities...")
    countries_added, countries_exists = add_countries()
    
    if countries_added > 0 or countries_exists > 0:
        print("\nStarting to add cities...")
        cities_added, cities_exists = add_cities()
        
        print("\nSummary:")
        print(f"Countries added: {countries_added}")
        print(f"Countries already exists: {countries_exists}")
        print(f"Cities added: {cities_added}")
        print(f"Cities already exists: {cities_exists}")
    else:
        print("No countries were processed, check for errors.") 