TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_lead_stats",
            "description": "Counts leads by temperature within a specified number of days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["hot", "cold"]
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back."
                    }
                },
                "required": ["status", "days"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_lead_by_email",
            "description": "Finds a specific lead by email address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the lead."
                    }
                },
                "required": ["email"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "update_lead_temperature",
            "description": "Manually changes the temperature of a lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer"
                    },
                    "new_status": {
                        "type": "string",
                        "enum": ["hot", "cold"]
                    }
                },
                "required": ["id", "new_status"]
            }
        }
    }
]