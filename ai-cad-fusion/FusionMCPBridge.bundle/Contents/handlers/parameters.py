"""
Parameter-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import ValidationError, FusionAPIError


class CreateParameterHandler(BaseHandler):
    """Handler for create_parameter action"""
    
    def validate(self, args: dict) -> dict:
        """Validate parameter creation arguments"""
        # Use centralized validation service
        self.validators.validate_required_fields(args, ["name", "expression", "unit"])
        
        name = self.validators.validate_non_empty_string(args["name"], "name")
        expression = str(args["expression"])
        unit = args["unit"]
        comment = args.get("comment", "")
        
        # Validate unit against allowlist
        self.validators.validate_unit(unit)
        
        # Validate comment type
        if comment is not None and not isinstance(comment, str):
            raise ValidationError("comment must be a string when provided")
        
        # Check for name collision (determinism requirement)
        self.validators.check_parameter_name_collision(name, self.context.design)
        
        return {
            "name": name,
            "expression": expression,
            "unit": unit,
            "comment": comment or ""
        }
    
    def execute(self, args: dict) -> dict:
        """Create the parameter"""
        design = self.context.design
        param = design.userParameters.add(
            args["name"],
            adsk.core.ValueInput.createByString(args["expression"]),
            args["unit"],
            args["comment"]
        )
        
        result = {
            "name": param.name,
            "expression": param.expression,
            "unit": param.unit
        }
        
        if param.comment:
            result["comment"] = param.comment
            
        return result


class UpdateParameterHandler(BaseHandler):
    """Handler for update_parameter action"""
    
    def validate(self, args: dict) -> dict:
        """Validate parameter update arguments"""
        self.validators.validate_required_fields(args, ["name"])
        
        name = self.validators.validate_non_empty_string(args["name"], "name")
        expression = args.get("expression")
        unit = args.get("unit")
        comment = args.get("comment")
        
        # Convert expression to string if provided
        if expression is not None:
            expression = str(expression)
        
        # Validate unit if provided
        if unit is not None:
            if not isinstance(unit, str):
                raise ValidationError("unit must be a string when provided")
            self.validators.validate_unit(unit)
        
        # Validate comment if provided
        if comment is not None and not isinstance(comment, str):
            raise ValidationError("comment must be a string when provided")
        
        # Ensure at least one field to update
        if expression is None and unit is None and comment is None:
            raise ValidationError("At least one of expression, unit, or comment must be provided")
        
        return {
            "name": name,
            "expression": expression,
            "unit": unit,
            "comment": comment
        }
    
    def execute(self, args: dict) -> dict:
        """Update the parameter"""
        design = self.context.design
        
        # Find the parameter
        target_param = None
        if design.userParameters:
            for p in design.userParameters:
                if p.name == args["name"]:
                    target_param = p
                    break
        if target_param is None:
            raise ValidationError(f"Parameter '{args['name']}' not found")
        
        # Update expression (Fusion will parse/validate)
        if args["expression"] is not None:
            target_param.expression = args["expression"]
        
        # Update unit if provided
        if args["unit"] is not None:
            try:
                target_param.unit = args["unit"]
            except Exception:
                # Some Fusion versions may not allow changing unit directly; embed in expression as fallback
                try:
                    # If expression wasn't provided, reuse existing expression
                    expr_base = args["expression"] if args["expression"] is not None else target_param.expression
                    target_param.expression = f"{expr_base} {args['unit']}".strip()
                except Exception as e:
                    raise FusionAPIError(f"Failed to update parameter unit: {str(e)}")
        
        # Update comment if provided
        if args["comment"] is not None:
            try:
                target_param.comment = args["comment"]
            except Exception as e:
                raise FusionAPIError(f"Failed to update parameter comment: {str(e)}")
        
        result = {
            "name": target_param.name,
            "expression": target_param.expression,
            "unit": target_param.unit
        }
        try:
            if hasattr(target_param, 'comment') and target_param.comment:
                result["comment"] = target_param.comment
        except Exception:
            pass
        return result
