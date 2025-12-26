"""Script to create a fraud detection rule"""
import asyncio
import sys
import json
from app.db import AsyncSessionLocal
from app.models import FraudRule


async def create_rule(rule_name: str, description: str, condition_json: str, actions_json: str, priority: int = 0):
    """Create a new fraud detection rule"""
    async with AsyncSessionLocal() as session:
        # Check if rule exists
        from sqlalchemy import select
        stmt = select(FraudRule).where(FraudRule.rule_name == rule_name)
        result = await session.execute(stmt)
        existing_rule = result.scalar_one_or_none()
        
        if existing_rule:
            print(f"Rule with name '{rule_name}' already exists!")
            return
        
        # Parse JSON
        try:
            condition = json.loads(condition_json)
            actions = json.loads(actions_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return
        
        # Create rule
        rule = FraudRule(
            rule_name=rule_name,
            rule_description=description,
            rule_condition=condition,
            rule_actions=actions,
            priority=priority,
            is_active=True
        )
        
        session.add(rule)
        await session.commit()
        print(f"Rule '{rule_name}' created successfully!")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python create_rule.py <rule_name> <description> <condition_json> <actions_json> [priority]")
        print("\nExample:")
        print('python create_rule.py "High Amount" "Flag transactions over $5000" \'{"field":"amount","operator":">","value":5000}\' \'{"risk_score":0.8,"flag":true}\' 10')
        sys.exit(1)
    
    rule_name = sys.argv[1]
    description = sys.argv[2]
    condition_json = sys.argv[3]
    actions_json = sys.argv[4]
    priority = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    
    asyncio.run(create_rule(rule_name, description, condition_json, actions_json, priority))

