from fastapi.responses import JSONResponse
from datetime import datetime
from fastapi import APIRouter,status
from fastapi_sqlalchemy import db

from ..schemas.customfieldSchema import GlobalVariableSchema
from ..models.customfields import Variable

from ..dependencies.auth import AuthHandler
auth_handler = AuthHandler()


router = APIRouter(
    prefix="/api/customfields/v1",
    tags=["Customfield"],
    responses={404: {"description": "Not found"}},
)


@router.post("/global_variable")
async def create_global_variable(schema:GlobalVariableSchema):
    """
    Create a custom variable 
    """
    try:
        types = ['String','Number','Boolean','Date','Array']
        
        if schema.type in types:

            # check not same name variable
            # var_names = [i[0] for i in db.session.query(Variable.name).filter_by(flow_id=schema.flowId).all()]
            # if var_names in var_names:
            #     return JSONResponse(status_code=404,content={"errorMessage":"Name already exists"})
            # create the variable
            var = Variable(name = schema.name,type = schema.type,flow_id=schema.flowId)
            db.session.add(var)
            db.session.commit()
            db.session.close()

            return JSONResponse(status_code=status.HTTP_201_CREATED,content={"message":"Created successfully"})
        else:
            return JSONResponse(status_code=404,content={"errorMessage":"Type is not correct"})
    except Exception as e:
        print(e,"at check user. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"errorMessage":"Can't create a variable"})

@router.get("/variables")
async def get_variables(flow_id:int):
    """
    Get all variable by flow_id 
    """
    try:
        var_list = []
        db_variables = db.session.query(Variable).filter_by(flow_id=flow_id).all()
        for i in db_variables:
            var_list.append({"id": i.id,"name":i.name,"type":i.type, "flow_id":i.flow_id})
            
        db.session.commit()
        db.session.close()
        return JSONResponse(status_code=status.HTTP_200_OK,content={"Variables":var_list})
        
    except Exception as e:
        print(e,"at check user. Time:", datetime.now())
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"errorMessage":"Can't create a variable"})
