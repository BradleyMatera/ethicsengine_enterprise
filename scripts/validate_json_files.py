from pydantic import ValidationError
from schemas.identity import Identity
from schemas.ethical_guidance import EthicalGuidance
from schemas.guardrail import Guardrail
import json

def validate_json(file_path, schema):
    with open(file_path, 'r') as file:
        data = json.load(file)
    errors = []
    for item in data:
        try:
            schema(**item)
        except ValidationError as e:
            errors.append(str(e))
    return errors

if __name__ == "__main__":
    files_to_validate = {
        "data/identities/default_identities.json": Identity,
        "data/guidances/default_guidances.json": EthicalGuidance,
        "data/guardrails/default_guardrails.json": Guardrail,
    }

    for file_path, schema in files_to_validate.items():
        print(f"Validating {file_path}...")
        errors = validate_json(file_path, schema)
        if errors:
            print(f"Errors in {file_path}:")
            for error in errors:
                print(error)
        else:
            print(f"{file_path} is valid.")
