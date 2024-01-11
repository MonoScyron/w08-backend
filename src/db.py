import json

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, Enum, CheckConstraint, Text, Table
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import validates, relationship
from sqlalchemy.ext.declarative import declarative_base

with open('./data.json', 'r') as file:
    data = json.load(file)
    threat_levels_enum = data.get('threat_levels')
    ranks_enum = data.get('ranks')
    traumas_enum = data.get('traumas')
    ego_types_enum = data.get('ego_types')
    threat_clocks = data.get('threat_clocks')

# * Tables

db = SQLAlchemy()

Base = db.Model  # declarative_base()

# Junction tables
project_department_association = Table(
    'project_department_association', Base.metadata,
    Column('department_id', Integer, ForeignKey('departments.id'), nullable=False),
    Column('project_id', Integer, ForeignKey('projects.id'), nullable=False)
)
"""Junction table for projects and departments"""

agent_ego_association = Table(
    'agent_ego_association', Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), nullable=False),
    Column('ego_id', Integer, ForeignKey('egos.id'), nullable=False)
)
"""Junction table for agents and egos"""

agent_ability_association = Table(
    'agent_ability_association', Base.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id'), nullable=False),
    Column('ability_id', Integer, ForeignKey('abilities.id'), nullable=False)
)
"""Junction table for agents and abilities"""


class Department(Base):
    """
    One-to-many with agents (assigned department)
    Many-to-many with projects (assigned projects)
    """
    __tablename__ = 'departments'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    agents = relationship("Agent", back_populates="department")
    projects = relationship("Project", secondary=project_department_association, back_populates="departments")

    # Columns
    name = Column(String, nullable=False)
    buffs = Column(ARRAY(String), default=[], nullable=True)  # ! Should be array
    """Department wide buffs for assigned agents"""
    rabbited = Column(Boolean, default=False, nullable=False)
    """If true, department is locked by rabbit protocol."""


class Abnormality(Base):
    """
    Many-to-one with tiles
    One-to-many with agents (suppressing/working on?)
    One-to-many with egos (obtained from)
    """
    __tablename__ = "abnormalities"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    tile_id = Column(Integer(), ForeignKey("tiles.id"), nullable=True)
    tile = relationship('Tile', back_populates='abnormalities')

    agents = relationship("Agent", back_populates="abnormality")
    egos = relationship("Ego", back_populates="abnormality")

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
        'management_show >= 0 AND management_show <= array_length(management_notes, 1)'), default=0,
                             nullable=False)
    """Show management notes up to and including this number. Must be less than or equal to len(management_notes)."""
    management_notes = Column(ARRAY(Text), default=[], nullable=False)  # ! Should be array
    story_show = Column(Integer, CheckConstraint('story_show >= 0 AND story_show <= array_length(stories, 1)'),
                        default=0,
                        nullable=False)
    """Show story up to and including this number. Must be less than or equal to len(stories)."""
    stories = Column(ARRAY(Text), default=[], nullable=False)  # ! Should be array

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
    def validate_clocks(self, key, value):
        if value < 0:
            raise ValueError("Research clocks must be positive")
        if value > threat_clocks[self.threat_level]:
            raise ValueError("Research clocks must be less than or equal to the corresponding value of threat clocks")
        return value

    clock_4_finished = Column(Boolean, default=False, nullable=False)
    """True if research clock 4 is finished"""

    player_notes = Column(Text, nullable=True)


class Agent(Base):
    """
    Many-to-one with tiles
    Many-to-one with departments (assigned department)
    Many-to-one with abnormalities (suppressing/working on?)
    Many-to-many with egos (obtained egos)
    Many-to-many with abilities (obtained abilities)
    One-to-many with harms (obtained harms)
    """
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    tile_id = Column(Integer, ForeignKey('tiles.id'), nullable=True)
    tile = relationship('Tile', back_populates='agents')
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    department = relationship('Department', back_populates='agents')
    abnormality_id = Column(Integer, ForeignKey('abnormalities.id'), nullable=True)
    abnormality = relationship('Abnormality', back_populates='agents')

    egos = relationship('Ego', secondary=agent_ego_association, back_populates='agents')
    abilities = relationship('Ability', secondary=agent_ability_association, back_populates='agents')

    harms = relationship('Harm', back_populates='agent')

    # Columns
    name = Column(String, nullable=False)
    blurb = Column(String, nullable=True)
    """Flavor text blurb"""
    current_status = Column(String, nullable=True)
    """What the agent is currently doing"""
    character_notes = Column(Text, nullable=True)
    rank = Column(Enum(*ranks_enum, name='rank_enum'), nullable=False)

    physical_heal = Column(Integer, CheckConstraint('physical_heal >= 0 AND physical_heal <= 4'), default=0,
                           nullable=False)
    """Current count of physical healing clock. Value=[0...4]."""
    mental_heal = Column(Integer, CheckConstraint('mental_heal >= 0 AND mental_heal <= 4'), default=0, nullable=False)
    """Current count of mental healing clock. Value=[0...4]."""

    stress = Column(Integer, default=0, nullable=False)
    """Value=[0...6] if rank="Agent", else value=[0...8]."""

    @validates('stress')
    def validates_stress(self, key, value):
        if self.rank == 'Agent':
            if not (0 <= value <= 6):
                raise ValueError("For 'rank'=Agent agents, 'stress' must be between 0 and 6")
        else:
            if not (0 <= value <= 8):
                raise ValueError("For 'rank'=Captain agents, 'stress' must be between 0 and 8")
        return value

    traumas = Column(Enum(*traumas_enum, name='traumas_enum'), default=[], nullable=False)  # ! Should be array

    @validates('traumas')
    def validates_traumas(self, key, value):
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

    fortitude = Column(Integer, CheckConstraint('fortitude >= 0 AND fortitude <= 5'), default=0, nullable=False)
    """Fortitude level. Value=[0...5]."""
    prudence = Column(Integer, CheckConstraint('prudence >= 0 AND prudence <= 5'), default=0, nullable=False)
    """Prudence level. Value=[0...5]."""
    temperance = Column(Integer, CheckConstraint('temperance >= 0 AND temperance <= 5'), default=0, nullable=False)
    """Temperance level. Value=[0...5]."""
    justice = Column(Integer, CheckConstraint('justice >= 0 AND justice <= 5'), default=0, nullable=False)
    """Justice level. Value=[0...5]."""

    fortitude_tick = Column(Integer, CheckConstraint('fortitude_tick >= 0 AND fortitude_tick <= 6'), default=0,
                            nullable=False)
    """Fortitude clock count. Value=[0...6]."""
    prudence_tick = Column(Integer, CheckConstraint('prudence_tick >= 0 AND prudence_tick <= 6'), default=0,
                           nullable=False)
    """Prudence clock count. Value=[0...6]."""
    temperance_tick = Column(Integer, CheckConstraint('temperance_tick >= 0 AND temperance_tick <= 6'), default=0,
                             nullable=False)
    """Temperance clock count. Value=[0...6]."""
    justice_tick = Column(Integer, CheckConstraint('justice_tick >= 0 AND justice_tick <= 6'), default=0,
                          nullable=False)
    """Justice clock count. Value=[0...6]."""

    ability_tick = Column(Integer, default=0, nullable=False)
    """Ability clock count. Value=[0...8]."""

    force_lvl = Column(Integer, CheckConstraint('force_lvl >= 0 AND force_lvl <= 4'), default=0, nullable=False)
    """Level of force action. Note: Fortitude. Value=[0...4]."""
    endure_lvl = Column(Integer, CheckConstraint('endure_lvl >= 0 AND endure_lvl <= 4'), default=0, nullable=False)
    """Level of endure action. Note: Fortitude + Prudence. Value=[0...4]."""
    lurk_lvl = Column(Integer, CheckConstraint('lurk_lvl >= 0 AND lurk_lvl <= 4'), default=0, nullable=False)
    """Level of lurk action. Note: Fortitude + Temperance. Value=[0...4]."""
    rush_lvl = Column(Integer, CheckConstraint('rush_lvl >= 0 AND rush_lvl <= 4'), default=0, nullable=False)
    """Level of rush action. Note: Fortitude + Justice. Value=[0...4]."""
    observe_lvl = Column(Integer, CheckConstraint('observe_lvl >= 0 AND observe_lvl <= 4'), default=0, nullable=False)
    """Level of observe action. Note: Prudence. Value=[0...4]."""
    consort_lvl = Column(Integer, CheckConstraint('consort_lvl >= 0 AND consort_lvl <= 4'), default=0, nullable=False)
    """Level of consort action. Note: Prudence + Temperance. Value=[0...4]."""
    shoot_lvl = Column(Integer, CheckConstraint('shoot_lvl >= 0 AND shoot_lvl <= 4'), default=0, nullable=False)
    """Level of shoot action. Note: Prudence + Justice. Value=[0...4]."""
    protocol_lvl = Column(Integer, CheckConstraint('protocol_lvl >= 0 AND protocol_lvl <= 4'), default=0,
                          nullable=False)
    """Level of protocol action. Note: Temperance. Value=[0...4]."""
    discipline_lvl = Column(Integer, CheckConstraint('discipline_lvl >= 0 AND discipline_lvl <= 4'), default=0,
                            nullable=False)
    """Level of discipline action. Note: Temperance + Justice. Value=[0...4]."""
    skirmish_lvl = Column(Integer, CheckConstraint('skirmish_lvl >= 0 AND skirmish_lvl <= 4'), default=0,
                          nullable=False)
    """Level of skirmish action. Note: Justice. Value=[0...4]."""


class Project(Base):
    """
    Many-to-many with departments (projects assigned to department)
    """
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    departments = relationship('Department', secondary=project_department_association, back_populates='projects')

    # Columns
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    max_clock = Column(Integer, nullable=False)
    curr_tick = Column(Integer, CheckConstraint('curr_tick >= 0 AND curr_tick <= max_clock'), default=0, nullable=False)
    """Must be less than or equal to max_clock"""


class Ability(Base):
    """
    Many-to-many with agents (obtained abilities)
    """
    __tablename__ = "abilities"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    agents = relationship('Agent', secondary=agent_ability_association, back_populates='abilities')

    # Columns
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)


class Harm(Base):
    """
    Many-to-one with agents (obtained harms)
    """
    __tablename__ = "harms"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    agent = relationship('Agent', back_populates='harms')

    # Columns
    level = Column(Integer, CheckConstraint('level >= 0 AND level <= 3'), nullable=False)
    """Value=[0...3]"""
    is_physical = Column(Boolean, nullable=False)
    """True if harm is physical, False if harm is mental."""
    description = Column(Text, nullable=True)


class Ego(Base):
    """
    Many-to-many with agents (obtained ego)
    Many-to-one with abnormalities (obtained from)
    """
    __tablename__ = "egos"
    id = Column(Integer, primary_key=True, autoincrement=True)

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


class Clock(Base):
    """
    Many-to-one with agents (agent the clock belongs to)
    Many-to-one with abnormalities (abno the clock belongs to)
    Only one of these relationships will ever be non-null, the other will always be null
    """
    __tablename__ = 'clocks'
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True)
    agent = relationship('Agent', backref='clocks')
    abnormality_id = Column(Integer, ForeignKey('abnormalities.id'), nullable=True)
    abnormality = relationship('Abnormality', backref='clocks')

    relationship_constraint = CheckConstraint(
        "((agent_id IS NULL AND abnormality_id IS NOT NULL) OR (agent_id IS NOT NULL AND abnormality_id IS NULL))",
        name='relationship_constraint'
    )

    # Columns
    max_count = Column(Integer, nullable=False)
    tick_count = Column(Integer, CheckConstraint('tick_count < max_count'), nullable=False)
    """Must be less than or equal to max_count"""
    important = Column(Boolean, default=False, nullable=False)


class Tile(Base):
    """
    One-to-many with abnormalities
    One-to-many with agents
    If is_containment is False, relationship with abnormalities must be Null
    """
    __tablename__ = 'tiles'
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Relationships
    abnormalities = relationship('Abnormality', back_populates='tile')
    agents = relationship('Agent', back_populates='tile')

    y = Column(Integer, CheckConstraint('y >= 0 AND y <= 15'), nullable=False)
    x = Column(Integer, CheckConstraint('x >= 0 AND x <= 27'), nullable=False)
    can_place_containment = Column(Boolean, nullable=False)

    is_containment_unit = Column(Boolean,
                                 CheckConstraint('can_place_containment = TRUE OR is_containment_unit = FALSE'),
                                 nullable=False)
    """Must be False if can_place_containment is False or when abnormalities is null"""

    @validates('is_containment_unit')
    def validates_null_abno(self, key, value):
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
