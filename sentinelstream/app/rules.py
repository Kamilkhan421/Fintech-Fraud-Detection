"""Dynamic Rule Engine for fraud detection"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import FraudRule


class RuleEngine:
    """Rule engine for evaluating fraud detection rules"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rules: List[FraudRule] = []
    
    async def load_rules(self):
        """Load active rules from database"""
        stmt = select(FraudRule).where(
            FraudRule.is_active == True
        ).order_by(FraudRule.priority.desc())
        
        result = await self.db.execute(stmt)
        self.rules = result.scalars().all()
    
    def evaluate_condition(self, condition: Dict[str, Any], transaction: Dict[str, Any]) -> bool:
        """Evaluate a single rule condition against transaction data"""
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if field not in transaction:
            return False
        
        transaction_value = transaction[field]
        
        # Type conversion for comparison
        if isinstance(value, (int, float)) and isinstance(transaction_value, str):
            try:
                transaction_value = float(transaction_value)
            except (ValueError, TypeError):
                return False
        
        # Evaluate based on operator
        operators = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            "in": lambda a, b: a in b if isinstance(b, list) else False,
            "not_in": lambda a, b: a not in b if isinstance(b, list) else True,
            "contains": lambda a, b: b in str(a) if isinstance(a, (str, list)) else False,
        }
        
        if operator in operators:
            try:
                return operators[operator](transaction_value, value)
            except (TypeError, ValueError):
                return False
        
        return False
    
    def evaluate_conditions(self, conditions: Dict[str, Any], transaction: Dict[str, Any]) -> bool:
        """
        Evaluate rule conditions.
        Supports AND/OR logic via 'logic' field: {"logic": "AND", "conditions": [...]}
        """
        if "logic" in conditions:
            logic = conditions.get("logic", "AND").upper()
            condition_list = conditions.get("conditions", [])
            
            if logic == "AND":
                return all(self.evaluate_condition(cond, transaction) for cond in condition_list)
            elif logic == "OR":
                return any(self.evaluate_condition(cond, transaction) for cond in condition_list)
            else:
                return False
        
        # Single condition
        return self.evaluate_condition(conditions, transaction)
    
    async def evaluate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate transaction against all active rules.
        Returns dict with rule_score, flags, and triggered rules.
        """
        if not self.rules:
            await self.load_rules()
        
        rule_score = 0.0
        triggered_rules = []
        flags = []
        
        for rule in self.rules:
            if self.evaluate_conditions(rule.rule_condition, transaction):
                # Rule matched - apply actions
                actions = rule.rule_actions or {}
                
                # Update risk score (take maximum)
                risk_score = actions.get("risk_score", 0.5)
                if risk_score > rule_score:
                    rule_score = risk_score
                
                # Collect flags
                if actions.get("flag", False):
                    flags.append(rule.rule_name)
                
                triggered_rules.append({
                    "rule_name": rule.rule_name,
                    "rule_id": rule.id,
                    "risk_score": risk_score
                })
        
        return {
            "rule_score": min(rule_score, 1.0),  # Cap at 1.0
            "triggered_rules": triggered_rules,
            "flags": flags
        }
    
    async def get_rule_by_id(self, rule_id: int) -> Optional[FraudRule]:
        """Get a specific rule by ID"""
        stmt = select(FraudRule).where(FraudRule.id == rule_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_rules(self) -> List[FraudRule]:
        """Get all rules"""
        stmt = select(FraudRule).order_by(FraudRule.priority.desc(), FraudRule.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

