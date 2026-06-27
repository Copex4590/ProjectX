# ============================================================================
# Project X
# AIS Protocol
# ============================================================================


class AISProtocol:

    @staticmethod
    def subscribe_message(api_key: str):

        return {
            "APIKey": api_key,
            "BoundingBoxes": [
                [
                    [45.00, 17.50],
                    [48.50, 22.50]
                ]
            ],
            "FilterMessageTypes": [
                "PositionReport",
                "ShipStaticData",
                "StaticDataReport"
            ]
        }
