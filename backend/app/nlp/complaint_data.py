"""
app/nlp/complaint_data.py
--------------------------------------------------------------------
Small, hand-written ENGLISH demo dataset of citizen traffic complaints
used to train the complaint classifier.

Each row is (text, category, priority). This is a demonstration
dataset (6 categories x 22 sentences) written for this project, NOT
real citizen data. A production system would train on real complaints
collected from a helpline/app and reviewed by traffic staff.

DEMO_COMPLAINTS below are separate, unseen sentences used to show the
model in the UI -- they are deliberately NOT part of the training set.
--------------------------------------------------------------------
"""

from __future__ import annotations

CATEGORIES = [
    "traffic_congestion",
    "accident",
    "signal_fault",
    "illegal_parking",
    "rash_driving",
    "road_damage",
]

# (text, priority)  -- category is the dict key
_TRAINING: dict[str, list[tuple[str, str]]] = {
    "traffic_congestion": [
        ("Heavy traffic jam on Ring Road, vehicles are not moving for the last 30 minutes.", "normal"),
        ("Huge congestion near the railway station every evening.", "normal"),
        ("Traffic is completely stuck at the main market crossing.", "normal"),
        ("Long queue of vehicles on the flyover, it takes an hour to cross.", "normal"),
        ("Bumper to bumper traffic near the school gate during pickup time.", "normal"),
        ("The highway is jammed for kilometers because of slow moving trucks.", "normal"),
        ("Too many vehicles at the bus stand junction, nothing is moving.", "normal"),
        ("Office hours traffic on the bridge is unbearable, please send police to manage it.", "normal"),
        ("Standstill traffic on the main road, an ambulance is stuck in the jam.", "urgent"),
        ("Severe jam near the hospital road, emergency vehicles cannot pass.", "urgent"),
        ("Vehicles are crawling on the expressway due to heavy rush.", "normal"),
        ("Traffic gridlock at the city center after the cricket match.", "normal"),
        ("Long jam at the toll plaza, hundreds of cars are waiting.", "normal"),
        ("Rush hour congestion on the university road gets worse every day.", "normal"),
        ("The whole lane is blocked with slow traffic near the mall.", "normal"),
        ("Roads are choked near the temple during the festival.", "normal"),
        ("Heavy rush at the crossing and no traffic police is present to manage the flow.", "normal"),
        ("Cars are queued up for two kilometers before the underpass.", "normal"),
        ("Jam on the airport road, passengers are missing their flights.", "normal"),
        ("Slow moving traffic on the bypass road is wasting a lot of time.", "normal"),
        ("Traffic jam is blocking the way to the fire station.", "urgent"),
        ("Peak hour jam at the main square, buses and autos are blocking each other.", "normal"),
    ],
    "accident": [
        ("Two cars collided at the crossing and people are injured.", "urgent"),
        ("A truck hit a motorcycle on the highway, the rider is lying on the road.", "urgent"),
        ("There was a bus accident near the bridge, many passengers are hurt.", "urgent"),
        ("Car overturned on the expressway, please send an ambulance.", "urgent"),
        ("A pedestrian was hit by a speeding car near the school.", "urgent"),
        ("Minor collision between two cars at the signal, nobody is hurt.", "normal"),
        ("A bike skidded and fell near the roundabout, the rider has minor scratches.", "normal"),
        ("Rear end crash at the toll plaza, traffic is slow but there are no injuries.", "normal"),
        ("A scooter and an auto rickshaw crashed, the driver is bleeding.", "urgent"),
        ("A vehicle crashed into the divider last night and the wreck is still on the road.", "normal"),
        ("Fatal accident on the national highway, a person is unconscious.", "urgent"),
        ("A truck lost control and hit a roadside shop.", "urgent"),
        ("Two bikes collided at the market road, both riders got up and are fine.", "normal"),
        ("Car fell into the roadside ditch, passengers are trapped inside.", "urgent"),
        ("Accident near the petrol pump, a vehicle caught fire.", "urgent"),
        ("A cyclist was knocked down by a tempo, he is not moving.", "urgent"),
        ("Small fender bender in the parking lot of the mall.", "normal"),
        ("A school van met with an accident, children are crying and some are injured.", "urgent"),
        ("Chain collision of several vehicles in heavy fog on the highway.", "urgent"),
        ("A car hit the electric pole and the wires are hanging on the road.", "urgent"),
        ("Minor scratch accident between a car and a bike at the lane entrance.", "normal"),
        ("An auto rickshaw turned over near the bridge, the driver got out safely.", "normal"),
    ],
    "signal_fault": [
        ("The traffic signal at the main crossing is not working since morning.", "normal"),
        ("All lights are blinking red at the junction and vehicles are confused.", "normal"),
        ("The green light stays on for only five seconds, it is too short.", "normal"),
        ("Signal is stuck on red for ten minutes, nobody knows when it will change.", "normal"),
        ("Traffic light pole is broken and hanging dangerously over the road.", "urgent"),
        ("Timer display of the signal is dead near the bus stand.", "normal"),
        ("The pedestrian signal never turns green, people cannot cross the road.", "normal"),
        ("Both sides are showing green at the same time at the crossing.", "urgent"),
        ("Signal lights are completely off at a busy intersection, cars are almost colliding.", "urgent"),
        ("Red light duration is too long at the hospital crossing.", "normal"),
        ("The yellow light is not working on the signal near the school.", "normal"),
        ("The traffic signal does not change at night and vehicles wait for no reason.", "normal"),
        ("Please repair the broken signal at the market road.", "normal"),
        ("Signal turned green but the arrow light for right turn is not working.", "normal"),
        ("The traffic signal is covered by tree branches and drivers cannot see it.", "normal"),
        ("The signal cycle is not synchronized, we get red at every crossing.", "normal"),
        ("Power failure has switched off all signals at the main square.", "normal"),
        ("A signal light fell on a parked car during the storm.", "urgent"),
        ("The lights at the junction are flickering and confusing drivers.", "normal"),
        ("No signal is working at the highway crossing and trucks are speeding through.", "urgent"),
        ("The countdown timer shows the wrong time at the crossing.", "normal"),
        ("The signal keeps showing green for one road only, other roads wait forever.", "normal"),
    ],
    "illegal_parking": [
        ("Cars are parked on both sides of the narrow lane and block the road.", "normal"),
        ("A truck has been parked in front of my gate for two days.", "normal"),
        ("Vehicles are parked on the footpath and pedestrians have to walk on the road.", "normal"),
        ("Illegal parking outside the market is creating a bottleneck.", "normal"),
        ("Someone parked a car in the no parking zone near the bank.", "normal"),
        ("Bikes are parked on the zebra crossing every day.", "normal"),
        ("A bus is parked on the main road and blocking the turn.", "normal"),
        ("Cars are double parked outside the school during drop off.", "normal"),
        ("A car is parked blocking the emergency entrance of the hospital.", "urgent"),
        ("Auto rickshaws are parked at the corner and block the view of the signal.", "normal"),
        ("An abandoned vehicle has been parked on the roadside for weeks.", "normal"),
        ("Delivery trucks park on the main road during peak hours.", "normal"),
        ("People park their cars in the bus stop lane.", "normal"),
        ("Wrong parking near the metro station is blocking pedestrians.", "normal"),
        ("A tempo is parked right at the crossing and nobody moves it.", "normal"),
        ("Vehicles parked on the bridge are narrowing the road.", "normal"),
        ("Cars are parked in front of the ambulance bay, please tow them away.", "urgent"),
        ("Several two wheelers are parked in the no parking area near the temple.", "normal"),
        ("A big truck is parked overnight on the residential street.", "normal"),
        ("Vehicles are blocking the entrance of our society with illegal parking.", "normal"),
        ("Parked cars are blocking the ramp for wheelchair users.", "normal"),
        ("Illegal parking on the highway shoulder is dangerous for passing vehicles.", "urgent"),
    ],
    "rash_driving": [
        ("A car is driving at very high speed near the school zone.", "urgent"),
        ("Bike riders are doing stunts and wheelies on the highway.", "urgent"),
        ("A bus driver is driving rashly and overtaking from the wrong side.", "urgent"),
        ("Vehicles are moving in the wrong direction on a one way street.", "normal"),
        ("A truck is driving in the opposite direction on the expressway.", "urgent"),
        ("Many bikes jump the red light at this crossing every day.", "normal"),
        ("Drivers do not follow lane discipline and keep changing lanes suddenly.", "normal"),
        ("A car is zigzagging through traffic at high speed.", "urgent"),
        ("Bikers are racing at night on the flyover and making a lot of noise.", "normal"),
        ("Overspeeding vehicles near the hospital are a danger to patients.", "urgent"),
        ("People are using mobile phones while driving at the crossing.", "normal"),
        ("A tractor is going the wrong way on a busy road.", "normal"),
        ("A drunk driver is swerving across lanes on the bypass.", "urgent"),
        ("Autos take sudden u turns in the middle of the road.", "normal"),
        ("A car jumped the signal at full speed and nearly hit a pedestrian.", "urgent"),
        ("Riders without helmets are speeding on the main road.", "normal"),
        ("Heavy trucks are overspeeding in the residential area.", "normal"),
        ("A rash driver is chasing other vehicles at the highway entry.", "urgent"),
        ("Many cars cross the stop line and block the zebra crossing when the light is red.", "normal"),
        ("Illegal u turns near the market are causing near misses.", "normal"),
        ("A minibus is racing with another bus on the main road.", "urgent"),
        ("Vehicles come from the wrong side near the bridge and confuse everyone.", "normal"),
    ],
    "road_damage": [
        ("There is a big pothole in the middle of the road near the market.", "normal"),
        ("The road has deep cracks and is full of potholes after the rain.", "normal"),
        ("A manhole cover is missing on the main road and it is dangerous.", "urgent"),
        ("The road surface is broken near the bridge and bikes are skidding.", "normal"),
        ("A huge pit has formed on the highway and vehicles are swerving to avoid it.", "urgent"),
        ("Water logging on the road makes it impossible to see the potholes.", "normal"),
        ("The speed breaker is too high and damages the vehicles.", "normal"),
        ("Road markings are faded and drivers cannot see the lanes at night.", "normal"),
        ("Street lights are not working on this road and it is completely dark.", "normal"),
        ("The road divider is broken and lying on the road.", "urgent"),
        ("Loose gravel on the turn is making bikes slip.", "normal"),
        ("Construction material is left on the road and blocks half of it.", "normal"),
        ("A tree branch has fallen on the road and no one has removed it.", "normal"),
        ("The bridge expansion joint is damaged and makes a loud noise when vehicles pass.", "urgent"),
        ("An open drain without a cover near the bus stop, a child can fall in.", "urgent"),
        ("The road is dug up for cable work and was never repaired.", "normal"),
        ("Uneven road surface is causing back pain to bus passengers.", "normal"),
        ("A sinkhole has appeared near the crossing, please barricade it.", "urgent"),
        ("Faded zebra crossing and no road signs near the school.", "normal"),
        ("The footpath tiles are broken and people are tripping.", "normal"),
        ("An oil spill on the road is making it very slippery.", "urgent"),
        ("Potholes on the service road are damaging my car tyres.", "normal"),
    ],
}

# Unseen sentences for the UI demo (NOT in the training set above).
DEMO_COMPLAINTS: list[str] = [
    "There is a massive jam outside the stadium and nobody is moving.",
    "A motorcycle and a car crashed at the junction, the biker is bleeding badly.",
    "The signal near the college has been dead for three hours.",
    "Someone has parked a van right across the entrance of our lane.",
    "A speeding SUV is overtaking from the wrong side near the school.",
    "Deep pothole near the bus stop, two bikes have already fallen.",
    "The lights at the crossing are blinking and cars are not sure who should go.",
    "Trucks are stuck in a long queue on the bridge since morning.",
    "An open manhole on the main road is a danger to everyone.",
    "Cars are parked on the footpath outside the shopping complex.",
]


def get_training_rows() -> list[tuple[str, str, str]]:
    """Flattened (text, category, priority) rows for training."""
    rows: list[tuple[str, str, str]] = []
    for category, items in _TRAINING.items():
        for text, priority in items:
            rows.append((text, category, priority))
    return rows
