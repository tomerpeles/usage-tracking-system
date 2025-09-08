from datetime import datetime
from typing import Any, Dict, Optional

from shared.models.enums import ServiceType, BillingUnit


def calculate_event_cost(
    event_data: Dict[str, Any], 
    billing_rule: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Calculate cost for an event based on billing rules"""
    
    if not billing_rule:
        # Return zero cost if no billing rule found
        return {
            "total_cost": 0.0,
            "billing_unit": "unknown",
            "unit_count": 0,
            "rate_per_unit": 0.0,
            "calculation_method": "none",
            "calculated_at": datetime.utcnow(),
        }
    
    service_type = event_data.get("service_type")
    metrics = event_data.get("metrics", {})
    
    billing_unit = billing_rule.get("billing_unit", BillingUnit.REQUESTS)
    rate_per_unit = billing_rule.get("rate_per_unit", 0.0)
    calculation_method = billing_rule.get("calculation_method", "multiply")
    minimum_charge = billing_rule.get("minimum_charge")
    
    # Calculate unit count based on service type and billing unit
    unit_count = _calculate_unit_count(service_type, billing_unit, metrics)
    
    # Calculate base cost
    if calculation_method == "multiply":
        base_cost = unit_count * rate_per_unit
    elif calculation_method == "sum":
        base_cost = sum(metrics.values()) * rate_per_unit
    else:
        # Custom calculation - would need to implement expression evaluation
        base_cost = unit_count * rate_per_unit
    
    # Apply minimum charge if specified
    total_cost = max(base_cost, minimum_charge or 0.0)
    
    # Apply tiered rates if configured
    tiered_rates = billing_rule.get("tiered_rates")
    if tiered_rates:
        total_cost = _apply_tiered_rates(unit_count, tiered_rates, rate_per_unit)
    
    return {
        "total_cost": round(total_cost, 6),
        "billing_unit": billing_unit,
        "unit_count": unit_count,
        "rate_per_unit": rate_per_unit,
        "calculation_method": calculation_method,
        "base_cost": round(base_cost, 6),
        "minimum_charge": minimum_charge,
        "calculated_at": datetime.utcnow(),
    }


def _calculate_unit_count(service_type: str, billing_unit: str, metrics: Dict[str, Any]) -> float:
    """Calculate the unit count for billing based on service type and unit"""
    
    if service_type == ServiceType.LLM_SERVICE:
        if billing_unit == BillingUnit.TOKENS:
            return metrics.get("total_tokens", 0)
        elif billing_unit == BillingUnit.REQUESTS:
            return 1
        
    elif service_type == ServiceType.DOCUMENT_PROCESSOR:
        if billing_unit == BillingUnit.PAGES:
            return metrics.get("pages_processed", 0)
        elif billing_unit == BillingUnit.BYTES:
            return metrics.get("file_size_bytes", 0)
        elif billing_unit == BillingUnit.REQUESTS:
            return 1
            
    elif service_type == ServiceType.API_SERVICE:
        if billing_unit == BillingUnit.REQUESTS:
            return metrics.get("request_count", 1)
        elif billing_unit == BillingUnit.BYTES:
            return (metrics.get("payload_size_bytes", 0) + 
                   metrics.get("response_size_bytes", 0))
        elif billing_unit == BillingUnit.MINUTES:
            response_time_ms = metrics.get("response_time_ms", 0)
            return response_time_ms / 60000  # Convert to minutes
    
    # Default to request count
    return 1


def _apply_tiered_rates(unit_count: float, tiered_rates: Dict[str, Any], base_rate: float) -> float:
    """Apply tiered pricing rates"""
    
    # Example tiered_rates structure:
    # {
    #   "tiers": [
    #     {"from": 0, "to": 1000, "rate": 0.01},
    #     {"from": 1000, "to": 10000, "rate": 0.008},
    #     {"from": 10000, "to": null, "rate": 0.005}
    #   ]
    # }
    
    tiers = tiered_rates.get("tiers", [])
    if not tiers:
        return unit_count * base_rate
    
    total_cost = 0.0
    remaining_units = unit_count
    
    for tier in tiers:
        tier_from = tier["from"]
        tier_to = tier.get("to")  # None means unlimited
        tier_rate = tier["rate"]
        
        if remaining_units <= 0:
            break
            
        if unit_count <= tier_from:
            continue
            
        # Calculate units in this tier
        if tier_to is None:
            # Unlimited tier
            tier_units = remaining_units
        else:
            tier_units = min(remaining_units, tier_to - tier_from)
        
        # Add cost for this tier
        total_cost += tier_units * tier_rate
        remaining_units -= tier_units
    
    return total_cost


def estimate_monthly_cost(
    daily_usage: Dict[str, Any],
    billing_rules: Dict[str, Any],
    days_in_month: int = 30
) -> Dict[str, Any]:
    """Estimate monthly cost based on daily usage patterns"""
    
    monthly_cost = 0.0
    cost_breakdown = {}
    
    for service_type, service_usage in daily_usage.items():
        service_rules = billing_rules.get(service_type, {})
        daily_cost = 0.0
        
        for provider, provider_usage in service_usage.items():
            provider_rules = service_rules.get(provider, {})
            if not provider_rules:
                continue
                
            # Simulate event data for cost calculation
            event_data = {
                "service_type": service_type,
                "metrics": provider_usage.get("metrics", {})
            }
            
            billing_info = calculate_event_cost(event_data, provider_rules)
            provider_daily_cost = billing_info["total_cost"]
            daily_cost += provider_daily_cost
            
            cost_breakdown[f"{service_type}_{provider}"] = {
                "daily_cost": provider_daily_cost,
                "monthly_cost": provider_daily_cost * days_in_month,
                "billing_unit": billing_info["billing_unit"],
                "unit_count": billing_info["unit_count"],
            }
        
        monthly_cost += daily_cost * days_in_month
    
    return {
        "estimated_monthly_cost": round(monthly_cost, 2),
        "cost_breakdown": cost_breakdown,
        "days_in_month": days_in_month,
        "estimated_at": datetime.utcnow(),
    }