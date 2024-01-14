import json
import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, Enum, CheckConstraint, Text, Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import validates, relationship

parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_json_path = os.path.join(parent_directory, 'data.json')
with open(data_json_path, 'r') as file:
    data = json.load(file)
    department_names_enum = data.get('departments').keys()
    threat_levels_enum = data.get('threat_levels')
    ranks_enum = data.get('ranks')
    traumas_enum = data.get('traumas')
    ego_types_enum = data.get('ego_types')
    threat_clocks = data.get('threat_clocks')

# * Tables

db = SQLAlchemy()


class Base(db.Model):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)


# Junction tables
project_department_association = Table(
    'project_department_association', Base.metadata,
    Column('department_id', Integer, ForeignKey('departments.id'), nullable=False),
    Column('project_id', Integer, ForeignKey('projects.id'), nullable=False)
)
"""Junction table for projects and departments"""

agent_ego_association = Table(
    'agent_ego_association', Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), nullable=True),
    Column('ego_id', Integer, ForeignKey('egos.id'), nullable=False)
)
"""Junction table for agents and egos"""

agent_ability_association = Table(
    'agent_ability_association', Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), nullable=True),
    Column('ability_id', Integer, ForeignKey('abilities.id'), nullable=False)
)
"""Junction table for agents and abilities"""

agent_clock_association = Table(
    'agent_clock_association', Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), nullable=True),
    Column('clock_id', Integer, ForeignKey('clocks.id'), nullable=True)
)
"""Junction table for agents and clocks"""

abnormality_clock_association = Table(
    'abnormality_clock_association', Base.metadata,
    Column('abnormality_id', Integer, ForeignKey('abnormalities.id'), nullable=True),
    Column('clock_id', Integer, ForeignKey('clocks.id'), nullable=True)
)
"""Junction table for abnos and clocks"""


class Facility(db.Model):
    """
    Global data, should only have 1 row at a time
    """
    __tablename__ = 'facilities'
    id = Column(Integer, default=1, primary_key=True)

    # Columns
    available_PE = Column(Integer, default=0, nullable=False)
    available_rabbits = Column(Integer, default=0, nullable=False)
    day = Column(Integer, default=0, nullable=False)
    shift = Column(Integer, CheckConstraint('shift >= 0 AND shift <= 2', name='shift_constraint'), default=0,
                   nullable=False)
    alert_level = Column(Integer,
                         CheckConstraint('alert_level >= 0 AND alert_level <= 3', name='alert_level_constraint'),
                         default=0, nullable=False)
    facility_constraint = CheckConstraint('id = 1')
    """Make sure table only has one row"""

    def serialize(self):
        return {
            'id': self.id,
            'available_PE': self.available_PE,
            'available_rabbits': self.available_rabbits,
            'day': self.day,
            'shift': self.shift,
            'alert_level': self.alert_level
        }


class Department(db.Model):
    """
    One-to-many with agents (assigned department)
    Many-to-many with projects (assigned projects)
    Should only have 5 rows at a time
    """
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)

    # Relationships
    agents = relationship("Agent", back_populates="department")
    projects = relationship("Project", secondary=project_department_association, back_populates="departments")

    # Columns
    name = Column(Enum(*department_names_enum, name='department_names_enum'), nullable=False)
    buffs = Column(ARRAY(String), default=[], nullable=False)
    """Department wide buffs for assigned agents"""
    rabbited = Column(Boolean, default=False, nullable=False)
    """If true, department is locked by rabbit protocol."""

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'agents': [agent.simple_serialize() for agent in self.agents],
            'projects': [project.simple_serialize() for project in self.projects],
            'buffs': self.buffs,
            'rabbited': self.rabbited
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Abnormality(Base):
    """
    Many-to-one with tiles
    Many-to-many with clocks
    One-to-many with agents (suppressing/working on?)
    One-to-many with egos (obtained from)
    """
    __tablename__ = "abnormalities"

    # Relationships
    tile_id = Column(Integer(), ForeignKey("tiles.id"), nullable=True)
    tile = relationship('Tile', back_populates='abnormalities')

    clocks = relationship("Clock", secondary=abnormality_clock_association, back_populates="abnormalities")
    agents = relationship("Agent", back_populates="abnormality")
    egos = relationship("Ego", back_populates="abnormality", cascade="all, delete-orphan")

    # Columns
    name = Column(String, nullable=False)
    abno_code = Column(String, nullable=False)
    blurb = Column(String, nullable=False)
    """Flavor text blurb"""
    current_status = Column(String, nullable=True)
    """What the abno is currently doing"""
    threat_level = Column(Enum(*threat_levels_enum, name='threat_levels_enum'), nullable=False)

    is_breaching = Column(Boolean, default=False, nullable=False)
    """If True, abno is breaching. Cannot be True when is_working is True."""
    is_working = Column(Boolean, default=False, nullable=False)
    """If True, abno is being worked on. Cannot be True when is_breaching is True."""
    breaching_xor_working = CheckConstraint(
        '(is_breaching = true AND NOT is_working) OR (is_working = true AND NOT is_breaching)',
        name='breaching_xor_working')

    description = Column(Text, nullable=False)
    damage_type = Column(String, nullable=False)
    favored_work = Column(String, nullable=False)
    disfavored_work = Column(String, nullable=False)
    can_breach = Column(Boolean, nullable=False)
    weaknesses = Column(String, nullable=False)
    resists = Column(String, nullable=False)

    management_show = Column(Integer, CheckConstraint(
        'management_show >= 0 AND management_show <= array_length(management_notes, 1)',
        name='management_show_constraint'), default=0,
                             nullable=False)
    """Show management notes up to and including this number. Must be less than or equal to len(management_notes)."""
    management_notes = Column(ARRAY(Text), default=[], nullable=False)
    story_show = Column(Integer, CheckConstraint('story_show >= 0 AND story_show <= array_length(stories, 1)',
                                                 name='story_show_constraint'),
                        default=0,
                        nullable=False)
    """Show story up to and including this number. Must be less than or equal to len(stories)."""
    stories = Column(ARRAY(Text), default=[], nullable=False)

    clock_1 = Column(Integer, default=0, nullable=False)
    """
    Tick count for research clock 1. Min 0, max value dependent on threat level. If at max value, clock is finished.
    """
    clock_2 = Column(Integer, default=0, nullable=False)
    """
    Tick count for research clock 2. Min 0, max value dependent on threat level. If at max value, clock is finished.
    """
    clock_3 = Column(Integer, default=0, nullable=False)
    """
    Tick count for research clock 3. Min 0, max value dependent on threat level. If at max value, clock is finished.
    """
    clock_4 = Column(Integer, default=0, nullable=False)
    """Tick count for research clock 4. Min 0, max value dependent on threat level."""

    @validates('clock_1', 'clock_2', 'clock_3', 'clock_4')
    def validate_clocks(self, value):
        if value < 0:
            raise ValueError("Research clocks must be positive")
        if value > threat_clocks[self.threat_level]:
            raise ValueError("Research clocks must be less than or equal to the corresponding value of threat clocks")
        return value

    clock_4_finished = Column(Boolean, default=False, nullable=False)
    """True if research clock 4 is finished"""

    player_notes = Column(Text, nullable=True)

    def serialize(self):
        return {
            'id': self.id,
            'tile_id': self.tile_id,
            'name': self.name,
            'agents': [agent.simple_serialize() for agent in self.agents] if self.agents else [],
            'egos': [ego.simple_serialize() for ego in self.egos] if self.egos else [],
            'abno_code': self.abno_code,
            'blurb': self.blurb,
            'current_status': self.current_status,
            'threat_level': self.threat_level,
            'is_breaching': self.is_breaching,
            'is_working': self.is_working,
            'description': self.description,
            'damage_type': self.damage_type,
            'favored_work': self.favored_work,
            'disfavored_work': self.disfavored_work,
            'can_breach': self.can_breach,
            'weaknesses': self.weaknesses,
            'resists': self.resists,
            'management_show': self.management_show,
            'management_notes': self.management_notes,
            'story_show': self.story_show,
            'stories': self.stories,
            'clock_1': self.clock_1,
            'clock_2': self.clock_2,
            'clock_3': self.clock_3,
            'clock_4': self.clock_4,
            'clock_4_finished': self.clock_4_finished,
            'player_notes': self.player_notes
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'tile_id': self.tile_id,
            'name': self.name,
            'abno_code': self.abno_code,
            'threat_level': self.threat_level
        }


class Agent(Base):
    """
    Many-to-one with tiles
    Many-to-one with departments (assigned department)
    Many-to-one with abnormalities (suppressing/working on?)
    Many-to-many with egos (obtained egos)
    Many-to-many with abilities (obtained abilities)
    Many-to-many with clocks
    One-to-many with harms (obtained harms)
    """
    __tablename__ = "agents"

    # Relationships
    tile_id = Column(Integer, ForeignKey('tiles.id'), nullable=True)
    tile = relationship('Tile', back_populates='agents')
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    department = relationship('Department', back_populates='agents')
    abnormality_id = Column(Integer, ForeignKey('abnormalities.id'), nullable=True)
    abnormality = relationship('Abnormality', back_populates='agents')

    egos = relationship('Ego', secondary=agent_ego_association, back_populates='agents')
    abilities = relationship('Ability',
                             secondary=agent_ability_association,
                             back_populates='agents')
    clocks = relationship("Clock", secondary=agent_clock_association, back_populates="agents")

    harms = relationship('Harm', back_populates='agent', cascade="all, delete-orphan")

    # Columns
    name = Column(String, nullable=False)
    blurb = Column(String, nullable=True)
    """Flavor text blurb"""
    current_status = Column(String, nullable=True)
    """What the agent is currently doing"""
    character_notes = Column(Text, nullable=True)
    rank = Column(Enum(*ranks_enum, name='rank_enum'), nullable=False)

    physical_heal = Column(Integer, CheckConstraint('physical_heal >= 0 AND physical_heal <= 4',
                                                    name='physical_heal_constraint'), default=0, nullable=False)
    """Current count of physical healing clock. Value=[0...4]."""
    mental_heal = Column(Integer,
                         CheckConstraint('mental_heal >= 0 AND mental_heal <= 4', name='mental_heal_constraint'),
                         default=0, nullable=False)
    """Current count of mental healing clock. Value=[0...4]."""

    stress = Column(Integer, default=0, nullable=False)
    """Value=[0...6] if rank="Agent", else value=[0...8]."""

    @validates('stress')
    def validates_stress(self, value):
        if self.rank == 'Agent':
            if not (0 <= value <= 6):
                raise ValueError("For 'rank'=Agent agents, 'stress' must be between 0 and 6")
        else:
            if not (0 <= value <= 8):
                raise ValueError("For 'rank'=Captain agents, 'stress' must be between 0 and 8")
        return value

    traumas = Column(ARRAY(Enum(*traumas_enum, name='traumas_enum')), default=[], nullable=False)

    @validates('traumas')
    def validates_traumas(self, value):
        if self.rank == 'Agent':
            if len(value) > 1:
                raise ValueError("For 'rank'=Agent agents, you can only have up to 1 'trauma'")
        else:
            if len(value) > 2:
                raise ValueError("For 'rank'=Agent agents, you can only have up to 2 'trauma'")
        return value

    is_visible = Column(Boolean, default=True, nullable=False)
    """If True, agent is shown on map"""
    agent_exp = Column(Integer, default=0, nullable=False)
    """Available ability clock and ego gift clock exp"""

    fortitude = Column(Integer, CheckConstraint('fortitude >= 0 AND fortitude <= 5', name='fortitude_constraint'),
                       default=0, nullable=False)
    """Fortitude level. Value=[0...5]."""
    prudence = Column(Integer, CheckConstraint('prudence >= 0 AND prudence <= 5', name='prudence_constraint'),
                      default=0, nullable=False)
    """Prudence level. Value=[0...5]."""
    temperance = Column(Integer, CheckConstraint('temperance >= 0 AND temperance <= 5', name='temperance_constraint'),
                        default=0, nullable=False)
    """Temperance level. Value=[0...5]."""
    justice = Column(Integer, CheckConstraint('justice >= 0 AND justice <= 5', name='justice_constraint'), default=0,
                     nullable=False)
    """Justice level. Value=[0...5]."""

    fortitude_tick = Column(Integer, CheckConstraint('fortitude_tick >= 0 AND fortitude_tick <= 6',
                                                     name='fortitude_tick_constraint'), default=0,
                            nullable=False)
    """Fortitude clock count. Value=[0...6]."""
    prudence_tick = Column(Integer, CheckConstraint('prudence_tick >= 0 AND prudence_tick <= 6',
                                                    name='prudence_tick_constraint'), default=0,
                           nullable=False)
    """Prudence clock count. Value=[0...6]."""
    temperance_tick = Column(Integer, CheckConstraint('temperance_tick >= 0 AND temperance_tick <= 6',
                                                      name='temperance_tick_constraint'), default=0,
                             nullable=False)
    """Temperance clock count. Value=[0...6]."""
    justice_tick = Column(Integer,
                          CheckConstraint('justice_tick >= 0 AND justice_tick <= 6', name='justice_tick_constraint'),
                          default=0,
                          nullable=False)
    """Justice clock count. Value=[0...6]."""

    ability_tick = Column(Integer, default=0, nullable=False)
    """Ability clock count. Value=[0...8]."""

    force_lvl = Column(Integer, CheckConstraint('force_lvl >= 0 AND force_lvl <= 4', name='force_lvl_constraint'),
                       default=0, nullable=False)
    """Level of force action. Note: Fortitude. Value=[0...4]."""
    endure_lvl = Column(Integer, CheckConstraint('endure_lvl >= 0 AND endure_lvl <= 4', name='endure_lvl_constraint'),
                        default=0, nullable=False)
    """Level of endure action. Note: Fortitude + Prudence. Value=[0...4]."""
    lurk_lvl = Column(Integer, CheckConstraint('lurk_lvl >= 0 AND lurk_lvl <= 4', name='lurk_lvl_constraint'),
                      default=0, nullable=False)
    """Level of lurk action. Note: Fortitude + Temperance. Value=[0...4]."""
    rush_lvl = Column(Integer, CheckConstraint('rush_lvl >= 0 AND rush_lvl <= 4', name='rush_lvl_constraint'),
                      default=0, nullable=False)
    """Level of rush action. Note: Fortitude + Justice. Value=[0...4]."""
    observe_lvl = Column(Integer,
                         CheckConstraint('observe_lvl >= 0 AND observe_lvl <= 4', name='observe_lvl_constraint'),
                         default=0, nullable=False)
    """Level of observe action. Note: Prudence. Value=[0...4]."""
    consort_lvl = Column(Integer,
                         CheckConstraint('consort_lvl >= 0 AND consort_lvl <= 4', name='consort_lvl_constraint'),
                         default=0, nullable=False)
    """Level of consort action. Note: Prudence + Temperance. Value=[0...4]."""
    shoot_lvl = Column(Integer, CheckConstraint('shoot_lvl >= 0 AND shoot_lvl <= 4', name='shoot_lvl_constraint'),
                       default=0, nullable=False)
    """Level of shoot action. Note: Prudence + Justice. Value=[0...4]."""
    protocol_lvl = Column(Integer,
                          CheckConstraint('protocol_lvl >= 0 AND protocol_lvl <= 4', name='protocol_lvl_constraint'),
                          default=0,
                          nullable=False)
    """Level of protocol action. Note: Temperance. Value=[0...4]."""
    discipline_lvl = Column(Integer, CheckConstraint('discipline_lvl >= 0 AND discipline_lvl <= 4',
                                                     name='discipline_lvl_constraint'), default=0,
                            nullable=False)
    """Level of discipline action. Note: Temperance + Justice. Value=[0...4]."""
    skirmish_lvl = Column(Integer,
                          CheckConstraint('skirmish_lvl >= 0 AND skirmish_lvl <= 4', name='skirmish_lvl_constraint'),
                          default=0,
                          nullable=False)
    """Level of skirmish action. Note: Justice. Value=[0...4]."""

    def serialize(self):
        return {
            'id': self.id,
            'tile_id': self.tile_id,
            'name': self.name,
            'department_id': self.department_id,
            'egos': [ego.simple_serialize() for ego in self.egos] if self.egos else [],
            'abilities': [ability.simple_serialize() for ability in self.abilities] if self.abilities else [],
            'harms': [harm.simple_serialize() for harm in self.harms] if self.harms else [],
            'abnormality_id': self.abnormality_id,
            'blurb': self.blurb,
            'current_status': self.current_status,
            'character_notes': self.character_notes,
            'rank': self.rank,
            'physical_heal': self.physical_heal,
            'mental_heal': self.mental_heal,
            'stress': self.stress,
            'traumas': self.traumas,
            'is_visible': self.is_visible,
            'agent_exp': self.agent_exp,
            'fortitude': self.fortitude,
            'prudence': self.prudence,
            'temperance': self.temperance,
            'justice': self.justice,
            'fortitude_tick': self.fortitude_tick,
            'prudence_tick': self.prudence_tick,
            'temperance_tick': self.temperance_tick,
            'justice_tick': self.justice_tick,
            'ability_tick': self.ability_tick,
            'force_lvl': self.force_lvl,
            'endure_lvl': self.endure_lvl,
            'lurk_lvl': self.lurk_lvl,
            'rush_lvl': self.rush_lvl,
            'observe_lvl': self.observe_lvl,
            'consort_lvl': self.consort_lvl,
            'shoot_lvl': self.shoot_lvl,
            'protocol_lvl': self.protocol_lvl,
            'discipline_lvl': self.discipline_lvl,
            'skirmish_lvl': self.skirmish_lvl
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'department_id': self.department_id,
            'rank': self.rank
        }


class Project(Base):
    """
    Many-to-one with departments (projects assigned to department)
    """
    __tablename__ = "projects"

    # Relationships
    departments = relationship('Department', secondary=project_department_association, back_populates='projects')

    # Columns
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    max_clock = Column(Integer, nullable=False)
    curr_tick = Column(Integer,
                       CheckConstraint('curr_tick >= 0 AND curr_tick <= max_clock', name='curr_tick_constraint'),
                       default=0, nullable=False)
    """Must be less than or equal to max_clock"""

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'departments': [department.simple_serialize() for department in
                            self.departments] if self.departments else [],
            'max_clock': self.max_clock,
            'curr_tick': self.curr_tick
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'max_clock': self.max_clock,
            'curr_tick': self.curr_tick
        }


class Ability(Base):
    """
    Many-to-many with agents (obtained abilities)
    """
    __tablename__ = "abilities"

    # Relationships
    agents = relationship('Agent', secondary=agent_ability_association, back_populates='abilities')

    # Columns
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    rank = Column(Enum(*ranks_enum, name='ranks_emum'), default='Agent', nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rank': self.rank,
            'agents': [agent.simple_serialize() for agent in self.agents] if self.agents else []
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rank': self.rank
        }


class Harm(Base):
    """
    Many-to-one with agents (obtained harms)
    """
    __tablename__ = "harms"

    # Relationships
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    agent = relationship('Agent', back_populates='harms')

    # Columns
    level = Column(Integer, CheckConstraint('level >= 0 AND level <= 3', name='level_constraint'), nullable=False)
    """Value=[0...3]"""
    is_physical = Column(Boolean, nullable=False)
    """True if harm is physical, False if harm is mental."""
    description = Column(Text, nullable=True)

    def serialize(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'level': self.level,
            'is_physical': self.is_physical,
            'description': self.description
        }

    def simple_serialize(self):
        return self.serialize()


class Ego(Base):
    """
    Many-to-many with agents (obtained ego)
    Many-to-one with abnormalities (obtained from)
    """
    __tablename__ = "egos"

    # Relationships
    agents = relationship('Agent', secondary=agent_ego_association, back_populates='egos')

    abnormality_id = Column(Integer, ForeignKey('abnormalities.id'), nullable=False)
    abnormality = relationship('Abnormality', back_populates='egos')

    # Columns
    type = Column(Enum(*ego_types_enum, name='ego_types_enum'), nullable=False)
    name = Column(String, nullable=False)
    grade = Column(Enum(*threat_levels_enum, name='threat_levels_enum'), nullable=False)
    effect = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    max_extracted = Column(Integer,
                           CheckConstraint("max_extracted IS NULL OR type != 'Gift'", name='max_extracted_constraint'),
                           nullable=True)
    """Maximum amount of ego that can be extracted. Should be Null if type="Gift"."""

    def serialize(self):
        return {
            'id': self.id,
            'abnormality_id': self.abnormality_id,
            'type': self.type,
            'name': self.name,
            'agents': [agent.simple_serialize() for agent in self.agents] if self.agents else [],
            'grade': self.grade,
            'effect': self.effect,
            'description': self.description,
            'max_extracted': self.max_extracted
        }

    def simple_serialize(self):
        return {
            'id': self.id,
            'abnormality_id': self.abnormality_id,
            'type': self.type,
            'name': self.name,
            'grade': self.grade
        }


class Clock(Base):
    """
    Many-to-many with agents (agent the clock belongs to)
    Many-to-many with abnormalities (abno the clock belongs to)
    """
    __tablename__ = 'clocks'

    # Relationships
    agents = relationship("Agent", secondary=agent_clock_association, back_populates="clocks")
    abnormalities = relationship("Abnormality", secondary=abnormality_clock_association, back_populates="clocks")

    # Columns
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    max_count = Column(Integer, nullable=False)
    tick_count = Column(Integer, CheckConstraint('tick_count <= max_count', name='tick_count_constraint'), default=0,
                        nullable=False)
    """Must be less than or equal to max_count"""
    important = Column(Boolean, default=False, nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'max_count': self.max_count,
            'tick_count': self.tick_count,
            'important': self.important
        }


class Tile(Base):
    """
    One-to-many with abnormalities
    One-to-many with agents
    If is_containment is False, relationship with abnormalities must be Null
    """
    __tablename__ = 'tiles'

    # Relationships
    abnormalities = relationship('Abnormality', back_populates='tile')
    agents = relationship('Agent', back_populates='tile')

    y = Column(Integer, CheckConstraint('y >= 0 AND y <= 15', name='y_constraint'), nullable=False)
    x = Column(Integer, CheckConstraint('x >= 0 AND x <= 27', name='x_constraint'), nullable=False)
    can_place_containment = Column(Boolean, nullable=False)

    is_containment_unit = Column(Boolean,
                                 CheckConstraint('can_place_containment = TRUE OR is_containment_unit = FALSE',
                                                 name='is_containment_unit_constraint'),
                                 nullable=False)
    """Must be False if can_place_containment is False or when abnormalities is null"""

    @validates('is_containment_unit')
    def validates_null_abno(self, value):
        if self.abnormalities is not None or not value:
            raise ValueError(f'is_containment_unit must be False when no abnormalities are assigned to tile')
        return value

    is_working = Column(Boolean, nullable=True)
    """Must be null if relationship with abnormalities is null"""
    meltdown = Column(Boolean, nullable=True)
    """Must be null if relationship with abnormalities is null"""
    work_type = Column(String, nullable=True)
    """Must be null if relationship with abnormalities is null"""
    engagement_status = Column(String, nullable=True)
    """Must be null if relationship with abnormalities is null"""

    @validates('is_working', 'meltdown', 'work_type', 'engagement_status')
    def validates_null_abno(self, key, value):
        if self.abnormalities is not None or value is None:
            raise ValueError(f'{key} must be NULL when no abnormalities are assigned to tile')
        return value

    def serialize(self):
        return {
            'id': self.id,
            'abnormalities': [abnormality.simple_serialize() for abnormality in
                              self.abnormalities] if self.abnormalities else [],
            'agents': [agent.simple_serialize() for agent in self.agents] if self.agents else [],
            'y': self.y,
            'x': self.x,
            'can_place_containment': self.can_place_containment,
            'is_containment_unit': self.is_containment_unit,
            'is_working': self.is_working,
            'meltdown': self.meltdown,
            'work_type': self.work_type,
            'engagement_status': self.engagement_status
        }
