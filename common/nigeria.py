"""Synthetic Nigerian identity generator. Formats: schemas/pii_formats.md."""
from __future__ import annotations
import random
from faker import Faker

FIRST_NAMES = [
    "Chiamaka", "Emeka", "Ngozi", "Chukwuemeka", "Adaeze", "Obinna", "Ifeoma", "Nnamdi", "Chinedu", "Amara",
    "Adebayo", "Folake", "Oluwaseun", "Temitope", "Yetunde", "Babatunde", "Funmilayo", "Olumide", "Abiodun", "Kehinde",
    "Aisha", "Musa", "Fatima", "Ibrahim", "Zainab", "Abubakar", "Hauwa", "Usman", "Halima", "Sani",
    "Efe", "Osas", "Ese", "Eghosa", "Tega", "Ebiere", "Preye", "Tamuno", "Ladi", "Blessing",
]
LAST_NAMES = [
    "Okonkwo", "Okafor", "Nwachukwu", "Eze", "Obi", "Nwosu", "Igwe", "Chukwu", "Onyeka", "Udeh",
    "Adeyemi", "Okoro", "Balogun", "Adewale", "Oyelaran", "Akinwande", "Olawale", "Bankole", "Oni", "Fashola",
    "Abdullahi", "Bello", "Mohammed", "Yusuf", "Sulaiman", "Danjuma", "Garba", "Lawal", "Shehu", "Aliyu",
    "Omoregie", "Igbinedion", "Edet", "Akpan", "Bassey", "Okoh", "Briggs", "Ebiwari", "Dakolo", "Ojukwu",
]
STATES_LGAS = {
    "Lagos": ["Eti-Osa", "Ikeja", "Surulere", "Alimosho", "Kosofe", "Lagos Island"],
    "FCT": ["Abuja Municipal", "Gwagwalada", "Bwari", "Kuje"],
    "Rivers": ["Port Harcourt", "Obio-Akpor", "Eleme"],
    "Kano": ["Nassarawa", "Fagge", "Kano Municipal", "Tarauni"],
    "Oyo": ["Ibadan North", "Ibadan South-West", "Ogbomosho North"],
    "Enugu": ["Enugu North", "Enugu South", "Nsukka"],
    "Kaduna": ["Kaduna North", "Kaduna South", "Zaria"],
    "Anambra": ["Awka South", "Onitsha North", "Nnewi North"],
    "Delta": ["Warri South", "Oshimili South", "Uvwie"],
    "Edo": ["Oredo", "Egor", "Ikpoba-Okha"],
    "Akwa Ibom": ["Uyo", "Eket", "Ikot Ekpene"],
    "Plateau": ["Jos North", "Jos South"],
}
STATE_CODES = {"Lagos": "LAG", "FCT": "ABJ", "Rivers": "RIV", "Kano": "KAN", "Oyo": "OYO", "Enugu": "ENU",
               "Kaduna": "KAD", "Anambra": "ANA", "Delta": "DEL", "Edo": "EDO", "Akwa Ibom": "AKW", "Plateau": "PLA"}
STREETS = [
    "Adeola Odeku Street", "Awolowo Road", "Allen Avenue", "Herbert Macaulay Way", "Aba Road", "Ahmadu Bello Way",
    "Zik Avenue", "Bodija Estate Road", "Murtala Mohammed Way", "Olu Obasanjo Road", "Sapele Road", "Ring Road",
    "Ogui Road", "Airport Road", "Nnebisi Road", "Wetheral Road", "Oron Road", "Isaac John Street",
]
AREAS = ["Victoria Island", "GRA", "Ikoyi", "Wuse 2", "Garki", "Trans Amadi", "Bodija", "Independence Layout",
         "Ugbowo", "Nasarawa GRA", "Lekki Phase 1", "Maitama", "Asokoro", "Rumuola", "New Haven"]
MOBILE_PREFIXES = ["703", "705", "706", "803", "805", "806", "807", "810", "812", "813", "814", "816",
                   "903", "905", "906", "907", "908", "909", "913", "915", "916"]
BANKS = ["Access Bank", "Zenith Bank", "GTBank", "First Bank", "UBA", "Fidelity Bank", "Stanbic IBTC", "Union Bank"]


def generate(n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    fake = Faker("en_GB")
    fake.seed_instance(seed)
    out = []
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        state = rng.choice(list(STATES_LGAS))
        dob = fake.date_of_birth(minimum_age=18, maximum_age=70)
        out.append({
            "id": f"I{i:04d}",
            "first_name": first,
            "last_name": last,
            "date_of_birth": dob.strftime("%d/%m/%Y"),
            "email": f"{first}.{last}{rng.randint(1, 99)}@example.com".lower(),
            "phone": f"+234 {rng.choice(MOBILE_PREFIXES)} {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "address_line": f"{rng.randint(1, 120)} {rng.choice(STREETS)}, {rng.choice(AREAS)}",
            "lga": rng.choice(STATES_LGAS[state]),
            "state": state,
            "nin": "".join(str(rng.randint(0, 9)) for _ in range(11)),
            "bvn": "22" + "".join(str(rng.randint(0, 9)) for _ in range(9)),
            "tin": f"{rng.randint(10000000, 99999999)}-{rng.randint(1, 9):04d}",
            "bank_account": f"{rng.randint(0, 9999999999):010d}",
            "bank_name": rng.choice(BANKS),
            "passport_no": f"{rng.choice('ABC')}{rng.randint(10000000, 99999999)}",
            "licence_no": f"{STATE_CODES[state]}{rng.randint(10000, 99999)}{rng.choice('ABCDEFGH')}{rng.choice('ABCDEFGH')}{rng.randint(10, 99)}",
            "annual_income": str(rng.randint(60, 2500) * 10000),
        })
    return out
