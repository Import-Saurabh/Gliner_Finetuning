"""Bundled demo texts — short, self-contained geopolitical passages so the
demo works instantly even before anyone touches the live Wikipedia search.

Kept short (well under max_text_len) and written in a neutral, encyclopedic
tone consistent with the Geopolitical Wiki News Dataset the adapter was
trained on.
"""
from __future__ import annotations

from typing import Dict, List

SAMPLES: List[Dict[str, str]] = [
    {
        "id": "iran-israel",
        "title": "Iran–Israel conflict",
        "source": "Wiki-news style / synthetic",
        "text": (
            "The multifront campaign has put Iran under unprecedented pressure, "
            "forcing its fatigued population to endure still more strain. "
            "Iranian Supreme Leader Mojtaba Khamenei, meanwhile, remains "
            "conspicuously absent. Tuesday will mark his sixth month in hiding "
            "in an attempt to avoid the fate of his father and predecessor, "
            "Ayatollah Ali Khamenei, who was killed in an airstrike at the start "
            "of the US-Israeli war against Iran in late February. The Israel "
            "Defense Forces and United States Central Command have continued "
            "joint operations, while the United Nations Security Council met "
            "in New York to discuss a ceasefire proposal."
        ),
    },
    {
        "id": "ukraine-war",
        "title": "Russian invasion of Ukraine",
        "source": "Wiki-news style / synthetic",
        "text": (
            "Ukrainian President Volodymyr Zelenskyy met with NATO Secretary "
            "General Mark Rutte in Kyiv on Monday to discuss additional air "
            "defense support. The meeting followed a renewed missile barrage "
            "on Kharkiv by Russian forces earlier in the week. The European "
            "Union announced a fresh sanctions package targeting Russian "
            "energy exports, while the Kremlin dismissed the move as largely "
            "symbolic. Fighting has intensified around Bakhmut since late "
            "2023, with both the Ukrainian General Staff and Russia's Ministry "
            "of Defence issuing conflicting casualty reports."
        ),
    },
    {
        "id": "sudan-civil-war",
        "title": "Sudanese civil war",
        "source": "Wiki-news style / synthetic",
        "text": (
            "The Sudanese Armed Forces, led by General Abdel Fattah al-Burhan, "
            "have continued clashes with the Rapid Support Forces under "
            "Mohamed Hamdan Dagalo in Khartoum since April 2023. The African "
            "Union and the United Nations have both called for a humanitarian "
            "corridor into Darfur, where the World Food Programme warns of "
            "famine conditions. Egypt and Saudi Arabia have hosted several "
            "rounds of ceasefire talks, most recently in Jeddah."
        ),
    },
    {
        "id": "m23-congo",
        "title": "M23 offensive in DR Congo",
        "source": "Wiki-news style / synthetic",
        "text": (
            "The M23 rebel group seized further territory in North Kivu "
            "province in early 2025, prompting the Congolese government under "
            "President Félix Tshisekedi to accuse neighboring Rwanda of "
            "direct military support. The Southern African Development "
            "Community deployed a regional force to Goma, while the "
            "International Criminal Court opened a preliminary inquiry into "
            "reported atrocities. Qatar has since facilitated indirect talks "
            "between Kinshasa and Kigali."
        ),
    },
    {
        "id": "taiwan-strait",
        "title": "Taiwan Strait tensions",
        "source": "Wiki-news style / synthetic",
        "text": (
            "China's People's Liberation Army conducted large-scale naval "
            "drills around Taiwan in August, days after Taiwanese President "
            "Lai Ching-te transited through Hawaii. The United States "
            "reiterated its commitment to the Taiwan Relations Act, prompting "
            "a rebuke from China's Ministry of Foreign Affairs. Japan's "
            "Ministry of Defense separately reported increased Chinese coast "
            "guard activity near the Senkaku Islands the same week."
        ),
    },
]
