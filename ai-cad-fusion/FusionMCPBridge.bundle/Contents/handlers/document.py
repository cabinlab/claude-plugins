"""
Document-related handlers
"""
import adsk.core
import adsk.fusion
from handlers.base import BaseHandler
from core.errors import FusionAPIError, ValidationError


class GetDesignInfoHandler(BaseHandler):
    """Handler for get_design_info action"""
    
    def validate(self, args: dict) -> dict:
        """Validate get_design_info arguments (no args needed)"""
        # get_design_info requires no arguments
        return args
    
    def execute(self, args: dict) -> dict:
        """Execute get_design_info action - identical to monolithic version"""
        try:
            design = self.context.design
            
            # Get basic design information
            result = {
                "documentName": self.context.app.activeDocument.name,
                "units": design.unitsManager.defaultLengthUnits if design.unitsManager else "mm",
                "components": [],
                "bodies": [],
                "parameters": [],
                "sketches": []
            }

            # Document metadata (documentInfo)
            try:
                active_doc = self.context.app.activeDocument
                doc_info = {
                    "isCloudDocument": active_doc.dataFile is not None
                }
                if active_doc.dataFile:
                    doc_info["id"] = active_doc.dataFile.id
                    doc_info["cloudId"] = active_doc.dataFile.id
                    if hasattr(active_doc.dataFile, 'parentProject') and active_doc.dataFile.parentProject:
                        doc_info["projectName"] = active_doc.dataFile.parentProject.name
                    if hasattr(active_doc.dataFile, 'parentFolder') and active_doc.dataFile.parentFolder:
                        doc_info["folderPath"] = active_doc.dataFile.parentFolder.name
                    if hasattr(active_doc.dataFile, 'versionNumber'):
                        doc_info["versionNumber"] = active_doc.dataFile.versionNumber
                    if hasattr(active_doc.dataFile, 'lastModified') and active_doc.dataFile.lastModified:
                        try:
                            doc_info["lastModified"] = active_doc.dataFile.lastModified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        except:
                            pass
                if hasattr(active_doc, 'fullPath') and active_doc.fullPath:
                    doc_info["fullPath"] = active_doc.fullPath
                result["documentInfo"] = doc_info
            except Exception:
                # documentInfo is optional; ignore failures
                pass
            
            # Get root component info
            root_comp = design.rootComponent
            
            # List components (simplified for v0)
            try:
                # Try the proper API first
                for i, comp in enumerate(design.allComponents):
                    result["components"].append({
                        "index": i,
                        "name": comp.name,
                        "isRoot": comp == root_comp
                    })
            except Exception as e:
                # Fallback: just list the root component
                result["components"].append({
                    "index": 0,
                    "name": root_comp.name,
                    "isRoot": True
                })
            
            # List bodies (simplified for v0)
            try:
                for i, body in enumerate(root_comp.bRepBodies):
                    result["bodies"].append({
                        "index": i,
                        "name": body.name,
                        "bodyType": "BRep"
                    })
            except Exception as e:
                # Bodies might not be accessible
                result["bodies"] = []
            
            # List user parameters (simplified for v0)
            if design.userParameters:
                for i, param in enumerate(design.userParameters):
                    p = {
                        "index": i,
                        "name": param.name,
                        "expression": param.expression,
                        "unit": param.unit,
                        "value": param.value
                    }
                    try:
                        # Include non-empty comments to aid human/agent understanding
                        if hasattr(param, 'comment') and param.comment:
                            p["comment"] = param.comment
                    except Exception:
                        pass
                    result["parameters"].append(p)
            
            # List sketches (added for create_sketch support)
            try:
                for i, sketch in enumerate(root_comp.sketches):
                    result["sketches"].append({
                        "index": i,
                        "name": sketch.name,
                        "isVisible": sketch.isVisible
                    })
            except Exception as e:
                # Sketches might not be accessible
                result["sketches"] = []
            
            return result
            
        except Exception as e:
            raise FusionAPIError(f"Failed to get design info: {str(e)}")


class ListOpenDocumentsHandler(BaseHandler):
    """Handler for list_open_documents action"""
    
    def validate(self, args: dict) -> dict:
        """No arguments needed for list_open_documents"""
        return args
    
    def execute(self, args: dict) -> dict:
        """List all open documents"""
        try:
            documents = []
            
            # Iterate through all open documents
            for i in range(self.context.app.documents.count):
                doc = self.context.app.documents.item(i)
                
                # Basic document info
                doc_info = {
                    "name": doc.name,
                    "isActive": doc == self.context.app.activeDocument,
                    "isDirty": getattr(doc, 'isModified', False),
                    "isCloudDocument": doc.dataFile is not None
                }
                
                # Document ID - cloud ID if cloud, else local:<name>
                if doc.dataFile:
                    doc_info["id"] = doc.dataFile.id
                    doc_info["cloudId"] = doc.dataFile.id
                    
                    # Cloud metadata if available
                    if hasattr(doc.dataFile, 'parentProject') and doc.dataFile.parentProject:
                        doc_info["projectName"] = doc.dataFile.parentProject.name
                    if hasattr(doc.dataFile, 'parentFolder') and doc.dataFile.parentFolder:
                        doc_info["folderPath"] = doc.dataFile.parentFolder.name
                    if hasattr(doc.dataFile, 'versionNumber'):
                        doc_info["versionNumber"] = doc.dataFile.versionNumber
                    if hasattr(doc.dataFile, 'lastModified'):
                        try:
                            doc_info["lastModified"] = doc.dataFile.lastModified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        except:
                            pass
                else:
                    doc_info["id"] = f"local:{doc.name}"
                
                # Local file path if available
                if hasattr(doc, 'fullPath') and doc.fullPath:
                    doc_info["fullPath"] = doc.fullPath
                
                documents.append(doc_info)
            
            return documents
            
        except Exception as e:
            raise FusionAPIError(f"Failed to list open documents: {str(e)}")


class GetOpenDocumentInfoHandler(BaseHandler):
    """Handler for get_open_document_info action"""
    
    def validate(self, args: dict) -> dict:
        """Validate get_open_document_info arguments"""
        name = args.get("name")
        full_path = args.get("fullPath")
        
        # At least one identifier is optional (defaults to active)
        if name is not None:
            name = self.validators.validate_non_empty_string(name, "name")
        if full_path is not None:
            full_path = self.validators.validate_non_empty_string(full_path, "fullPath")
            
        return {
            "name": name,
            "fullPath": full_path
        }
    
    def execute(self, args: dict) -> dict:
        """Get info about specific open document"""
        try:
            name = args.get("name")
            full_path = args.get("fullPath")
            
            # Find target document
            target_doc = None
            
            if name or full_path:
                # Search by name or fullPath
                for i in range(self.context.app.documents.count):
                    doc = self.context.app.documents.item(i)
                    if ((name and doc.name == name) or 
                        (full_path and hasattr(doc, 'fullPath') and doc.fullPath == full_path)):
                        target_doc = doc
                        break
                
                if target_doc is None:
                    raise ValidationError(f"Document not found: name='{name}', fullPath='{full_path}'")
            else:
                # Default to active document
                target_doc = self.context.app.activeDocument
                if target_doc is None:
                    raise ValidationError("No active document and no name/fullPath specified")
            
            # Build document info (same shape as list_open_documents item)
            doc_info = {
                "name": target_doc.name,
                "isActive": target_doc == self.context.app.activeDocument,
                "isDirty": getattr(target_doc, 'isModified', False),
                "isCloudDocument": target_doc.dataFile is not None
            }
            
            # Document ID and cloud metadata
            if target_doc.dataFile:
                doc_info["id"] = target_doc.dataFile.id
                doc_info["cloudId"] = target_doc.dataFile.id
                
                if hasattr(target_doc.dataFile, 'parentProject') and target_doc.dataFile.parentProject:
                    doc_info["projectName"] = target_doc.dataFile.parentProject.name
                if hasattr(target_doc.dataFile, 'parentFolder') and target_doc.dataFile.parentFolder:
                    doc_info["folderPath"] = target_doc.dataFile.parentFolder.name
                if hasattr(target_doc.dataFile, 'versionNumber'):
                    doc_info["versionNumber"] = target_doc.dataFile.versionNumber
                if hasattr(target_doc.dataFile, 'lastModified'):
                    try:
                        doc_info["lastModified"] = target_doc.dataFile.lastModified.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    except:
                        pass
            else:
                doc_info["id"] = f"local:{target_doc.name}"
            
            # Local file path if available
            if hasattr(target_doc, 'fullPath') and target_doc.fullPath:
                doc_info["fullPath"] = target_doc.fullPath
            
            return doc_info
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to get document info: {str(e)}")


class OpenDocumentHandler(BaseHandler):
    """Handler for open_document action"""
    
    def validate(self, args: dict) -> dict:
        """Validate open_document arguments - exactly one of path or id/cloudId required"""
        path = args.get("path")
        file_id = args.get("id") or args.get("cloudId")
        read_only = args.get("read_only", False)
        
        # Exactly one of path or file_id must be provided
        if not path and not file_id:
            raise ValidationError("Must provide either 'path' (for local files) or 'id'/'cloudId' (for cloud files)")
        if path and file_id:
            raise ValidationError("Cannot provide both 'path' and 'id'/'cloudId' - choose one")
        
        if path is not None:
            path = self.validators.validate_non_empty_string(path, "path")
        if file_id is not None:
            file_id = self.validators.validate_non_empty_string(file_id, "id/cloudId")
            
        if not isinstance(read_only, bool):
            raise ValidationError("read_only must be a boolean")
            
        return {
            "path": path,
            "file_id": file_id,
            "read_only": read_only
        }
    
    def execute(self, args: dict) -> dict:
        """Open a document from local file or cloud DataFile ID"""
        app = self.context.app
        path = args.get("path")
        file_id = args.get("file_id")
        read_only = bool(args.get("read_only", False))
        
        doc = None
        
        try:
            if file_id:
                # Open a cloud DataFile
                data = getattr(app, "data", None)
                if not data:
                    raise FusionAPIError("Fusion data service unavailable for cloud file open")
                    
                data_file = data.findFileById(file_id)
                if not data_file:
                    raise ValidationError(f"Cloud DataFile not found for id '{file_id}'")
                
                # Try both open overloads for cloud files
                try:
                    doc = app.documents.open(data_file, read_only)
                except TypeError:
                    # Older signatures may not accept read_only
                    doc = app.documents.open(data_file)
                    
            else:
                # Open a local path
                # Try overload with read_only; fall back if not supported
                try:
                    doc = app.documents.open(path, read_only)
                except TypeError:
                    doc = app.documents.open(path)
            
            if not doc:
                raise FusionAPIError("Failed to open document")
            
            # Get document info
            result = {
                "documentName": doc.name
            }
            
            if hasattr(doc, "fullPath") and doc.fullPath:
                result["fullPath"] = doc.fullPath
                
            # Optionally include default units when available
            try:
                design = doc.products.item(0)
                if design and hasattr(design, "unitsManager") and design.unitsManager:
                    result["units"] = design.unitsManager.defaultLengthUnits
            except Exception:
                pass  # Units optional
                
            return result
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to open document: {str(e)}")


class FocusDocumentHandler(BaseHandler):
    """Handler for focus_document action"""
    
    def validate(self, args: dict) -> dict:
        """Validate focus_document arguments"""
        name = args.get("name")
        full_path = args.get("fullPath")
        
        if not name and not full_path:
            raise ValidationError("Must provide either 'name' or 'fullPath'")
        
        if name is not None:
            name = self.validators.validate_non_empty_string(name, "name")
        if full_path is not None:
            full_path = self.validators.validate_non_empty_string(full_path, "fullPath")
            
        return {
            "name": name,
            "fullPath": full_path
        }
    
    def execute(self, args: dict) -> dict:
        """Focus/activate a document"""
        try:
            name = args.get("name")
            full_path = args.get("fullPath")
            
            # Find target document
            target_doc = None
            for i in range(self.context.app.documents.count):
                doc = self.context.app.documents.item(i)
                if ((name and doc.name == name) or 
                    (full_path and hasattr(doc, 'fullPath') and doc.fullPath == full_path)):
                    target_doc = doc
                    break
            
            if target_doc is None:
                raise ValidationError(f"Document not found: name='{name}', fullPath='{full_path}'")
            
            # Activate the document
            target_doc.activate()
            
            return {
                "documentName": target_doc.name
            }
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to focus document: {str(e)}")


class CloseDocumentHandler(BaseHandler):
    """Handler for close_document action"""
    
    def validate(self, args: dict) -> dict:
        """Validate close_document arguments"""
        save = args.get("save", False)
        
        if not isinstance(save, bool):
            raise ValidationError("save must be a boolean")
            
        return {
            "save": save
        }
    
    def execute(self, args: dict) -> dict:
        """Close the active document"""
        try:
            save = args["save"]
            
            active_doc = self.context.app.activeDocument
            if active_doc is None:
                raise ValidationError("No active document to close")
            
            # Close the document
            active_doc.close(save)
            
            return {
                "closed": True
            }
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to close document: {str(e)}")


class BackupDocumentHandler(BaseHandler):
    """Handler for backup_document action"""
    
    def validate(self, args: dict) -> dict:
        """Validate backup_document arguments"""
        path = args.get("path")
        format_type = args.get("format", "f3d")
        
        # Validate format
        if format_type not in ["f3d", "step"]:
            raise ValidationError("Format must be 'f3d' or 'step'")
        
        # Path is optional (auto-generated if not provided)
        if path is not None:
            path = self.validators.validate_non_empty_string(path, "path")
            
        return {
            "path": path,
            "format": format_type
        }
    
    def execute(self, args: dict) -> dict:
        """Backup the active document"""
        try:
            import os
            from datetime import datetime
            
            path = args.get("path")
            format_type = args["format"]
            
            active_doc = self.context.app.activeDocument
            if active_doc is None:
                raise ValidationError("No active document to backup")
            
            # Generate path if not provided
            if not path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_name = active_doc.name.replace('.', '_')  # Remove extension for clean naming
                filename = f"{doc_name}_backup_{timestamp}.{format_type}"
                
                # Use user's Documents folder
                user_docs = os.path.expanduser("~/Documents")
                path = os.path.join(user_docs, filename)
            
            # Perform backup based on format
            if format_type == "f3d":
                # Save as Fusion 360 file
                active_doc.saveAs(active_doc.name, path, "Fusion 360 Archive Files", "")
            elif format_type == "step":
                # Export as STEP file
                design = active_doc.products.item(0)
                if not design:
                    raise FusionAPIError("No design product found for STEP export")
                
                export_mgr = design.exportManager
                step_options = export_mgr.createSTEPExportOptions(path)
                export_mgr.execute(step_options)
            
            return {
                "savedTo": path
            }
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to backup document: {str(e)}")


class GetDocumentTypeHandler(BaseHandler):
    """Handler for get_document_type action"""
    
    def validate(self, args: dict) -> dict:
        """No arguments needed for get_document_type"""
        return args
    
    def execute(self, args: dict) -> dict:
        """Get the document type (parametric or direct)"""
        try:
            import adsk.fusion
            
            design = adsk.fusion.Design.cast(self.context.app.activeProduct)
            
            if design is None:
                # Not a design document
                return {
                    "type": "direct",
                    "designHistoryEnabled": False
                }
            
            # Check design type
            is_parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
            
            return {
                "type": "parametric" if is_parametric else "direct", 
                "designHistoryEnabled": is_parametric
            }
            
        except Exception as e:
            raise FusionAPIError(f"Failed to get document type: {str(e)}")


class GetDocumentStructureHandler(BaseHandler):
    """Handler for get_document_structure action"""
    
    def validate(self, args: dict) -> dict:
        """Validate get_document_structure arguments"""
        detail_level = args.get("detail", "low")
        
        if detail_level not in ["low", "high"]:
            raise ValidationError("Detail level must be 'low' or 'high'")
            
        return {
            "detail": detail_level
        }
    
    def execute(self, args: dict) -> dict:
        """Get structural overview of components and bodies"""
        try:
            detail_level = args["detail"]
            
            design = self.context.design
            root_comp = self.context.root_component
            
            # Components summary
            components = []
            try:
                for i, comp in enumerate(design.allComponents):
                    comp_info = {
                        "name": comp.name,
                        "occurrenceCount": comp.allOccurrences.count if hasattr(comp, 'allOccurrences') else 0,
                        "bodiesCount": comp.bRepBodies.count if hasattr(comp, 'bRepBodies') else 0
                    }
                    components.append(comp_info)
            except:
                # Fallback to root component only
                components.append({
                    "name": root_comp.name,
                    "occurrenceCount": 1,
                    "bodiesCount": root_comp.bRepBodies.count if hasattr(root_comp, 'bRepBodies') else 0
                })
            
            # Bodies summary
            bodies = []
            try:
                for i, body in enumerate(root_comp.bRepBodies):
                    body_info = {
                        "name": body.name,
                        "componentName": root_comp.name
                    }
                    
                    # Optional metrics for high detail
                    if detail_level == "high":
                        try:
                            if hasattr(body, 'physicalProperties'):
                                body_info["volume"] = body.physicalProperties.volume
                            if hasattr(body, 'boundingBox'):
                                bbox = body.boundingBox
                                body_info["bbox"] = {
                                    "min": {"x": bbox.minPoint.x, "y": bbox.minPoint.y, "z": bbox.minPoint.z},
                                    "max": {"x": bbox.maxPoint.x, "y": bbox.maxPoint.y, "z": bbox.maxPoint.z}
                                }
                        except:
                            pass  # Metrics are optional
                    
                    bodies.append(body_info)
            except:
                pass  # Bodies might not be accessible
            
            return {
                "components": components,
                "bodies": bodies
            }
            
        except ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise FusionAPIError(f"Failed to get document structure: {str(e)}")
