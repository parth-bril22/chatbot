
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON


Base  = declarative_base()

class Node(Base):
    __tablename__ = 'node'
    id = Column(Integer, primary_key = True)
    flow_id = Column(Integer)
    name = Column(String)
    data = Column(JSON)#but input will be as string/dict
    position = Column(JSON)#string/dict
    type = Column(String, ForeignKey("node_type.type", ondelete = "NO ACTION"))
    node_conn = relationship("NodeType", back_populates = "node_type_conn")
    node_sub_node =  relationship("SubNode",back_populates = 'sub_node_con')


class NodeType(Base):
    __tablename__ = 'node_type'
    id = Column(Integer, primary_key = True)
    type = Column(String, unique = True)
    params = Column(JSON)
    node_type_conn = relationship("Node", back_populates = "node_conn")


class Connections(Base):
    __tablename__ = 'connections'
    id = Column(Integer, primary_key = True)
    flow_id = Column(Integer)
    name = Column(String)
    source_node_id = Column(Integer)
    target_node_id = Column(Integer)
    sub_node_id = Column(Integer)

class SubNode(Base):
    __tablename__ = 'sub_node'
    id = Column(Integer, primary_key = True)
    flow_id = Column(Integer)
    data = Column(JSON)
    node_id = Column(Integer,ForeignKey("node.id", ondelete = "NO ACTION"))
    sub_node_con =  relationship("Node",back_populates = 'node_sub_node')
    
class CustomFields(Base):
    __tablename__ = 'custom_fields'
    id = Column(Integer, primary_key = True)
    flow_id = Column(Integer)
    name = Column(String)
    value = Column(String)
    type = Column(String, ForeignKey("custom_field_types.type", ondelete = "NO ACTION"))
    custom_field_conn = relationship("CustomFieldTypes", back_populates = "custom_field_type_conn")

class CustomFieldTypes(Base):
    __tablename__ = 'custom_field_types'
    type = Column(String, primary_key =True)
    datatype = Column(String)
    custom_field_type_conn = relationship("CustomFields", back_populates = "custom_field_conn")


class Diagram(Base):
    __tablename__ = 'diagram'
    id = Column(String, primary_key = True)
    name = Column(String)

