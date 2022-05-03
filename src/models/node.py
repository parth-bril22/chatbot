# import copy
# doc.config = copy.deepcopy(doc.config)

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON


Base  = declarative_base()

class Node(Base):
    __tablename__ = 'node'
    id = Column(Integer, primary_key = True)
    name = Column(String)
    path = Column(String)
    node_type = Column(String)
    properties = Column(JSON)#but input will be as string/dict
    position = Column(JSON)#string/dict
    type = Column(String, ForeignKey("node_type.type", ondelete = "NO ACTION"))
    node_conn = relationship("NodeType", back_populates = "node_type_conn")

class NodeType(Base):
    __tablename__ = 'node_type'
    id = Column(Integer, primary_key = True)
    type = Column(String, unique = True)
    params = Column(JSON)
    node_type_conn = relationship("Node", back_populates = "node_conn")


class Connections(Base):
    __tablename__ = 'connections'
    id = Column(Integer, primary_key = True)
    name = Column(String)
    source_node = Column(String)
    target_node = Column(String)
    sub_node = Column(String)

class CustomFields(Base):
    __tablename__ = 'custom_fields'
    id = Column(Integer, primary_key = True)
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

# nt = NodeType(id = '95', type = 'hellions', params = {"message":"world", "text":"no text"} )
# nt.params['text'] = 'yes text'
# session.add(nt)
# session.commit()

# # nt = copy.deepcopy(nt)
# # session.add(nt)
# # session.commit()
# # session.close()

# print(nt.params['text'])

