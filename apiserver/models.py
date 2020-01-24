"""
Central management for models based on Edge and Node classes with basic information
All nodes have a description so they are searchable in the Lucene text index. They also all have a hashkey which is
based on the node's attributes when first created to determine uniqueness. (Home.models.check_index_nodes)
TODO surface for UI configuration
"""
# Standard variables and classes used in each model
STRING = "string"
DATETIME = "datetime"
INTEGER = "integer"
FLOAT = "float"
'''
The Relationships that make up the graph based model. OUT and IN are defined as the properties that contain entity
records and allow indexing to prevent duplicate edges between nodes.
'''
Edge = {
    "class": "E",
    "out": "Link",
    "in": "Link"
    }
'''
The Entities that make up the graph based model. Define basic common properties. The hashkey is created on the fly 
within the Home.models.py file to hash all properties and values into a single key for comparison of uniqueness. The
Ext_key is used for any entities that have an id otherwise already. Description is provided to all to allow for text
search. Icon is provided for UX based rendering and title for any label also required in the UX.
'''
Node = {"class": "V",
        "Ext_key": STRING,
        "hashkey": STRING,
        "description": STRING,
        "icon": STRING,
        "title": STRING
        }
'''
All edges or relationships that will require indexing to prevent duplicate records/connections
'''
Edges = {
    "Discovered": Edge, "Has": Edge, "Included": Edge, "Initiated": Edge,
    "LocatedAt": Edge, "Owns": Edge, "Received": Edge, "References": Edge,
    "Tweeted": Edge, "TweetedFrom": Edge}
'''
Attributes that should be included to create a hashkey. Since they are created in the variable's order every time, it 
assures that any entity with the same attributes in a different order are created into a normalized hashkey.
'''
nodeKeys = [
    'class_name', 'title', 'FirstName', 'LastName', 'Gender', 'DateOfBirth', 'PlaceOfBirth',
    'Name', 'Owner', 'Classification', 'Category', 'Latitude', 'Longitude', 'userName',
    'EndDate', 'StartDate', 'DateCreated', 'Ext_key', 'category', 'pid', 'name', 'started', 'email',
    'searchValue', 'ipAddress', 'token', 'session', 'PhoneNumber', 'source', 'Entity']

OSINTModel = {
    "Person": dict(
        Node,
        DateOfBirth=DATETIME,
        PlaceOfBirth=STRING,
        FirstName=STRING,
        LastName=STRING,
        MidName=STRING,
        Gender=STRING
    ),
    "Object": dict(
        Node,
        Category=STRING,
        Tags=STRING
    ),
    "Organization": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        Members=INTEGER,
        Founded=DATETIME,
        Name=STRING,
        OtherNames=STRING,
        UCDP_id=STRING,
        ACLED_id=STRING,
        Source=STRING
    ),
    "Profile": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        Friends=INTEGER,
        Followers=INTEGER,
        Name=STRING,
        Screen_name=STRING,
        OtherNames=STRING,
        Posts=INTEGER,
        DateCreated=DATETIME,
        Source=STRING,
        url=STRING,
    ),
    "Post": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        RePosts=INTEGER,
        Likes=INTEGER,
        Author=STRING,
        Screen_name=STRING,
        OtherNames=STRING,
        Posts=INTEGER,
        DateCreated=DATETIME,
        StartDate=DATETIME,
        EndDate=DATETIME,
        Source=STRING,
        url=STRING,
    ),
    "Tag": dict(
        Node,
        Category=STRING,
        Source=STRING
    ),
    "Location": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        Latitude=FLOAT,
        Longitude=FLOAT,
        city=STRING,
        pop=INTEGER,
        country=STRING,
        iso3=STRING,
        province=STRING
    ),
    "Event": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME,
        Sources=STRING,
        Civilians=STRING,
        Deaths=STRING,
        Origin=STRING,
        UCDP_id=STRING
    ),
    "Case": dict(
        Node,
        Name=STRING,
        Owners=STRING,
        StartDate=DATETIME,
        LastUpdate=DATETIME,
        EndDate=DATETIME,
        CreatedBy=STRING,
        Members=STRING,
        Classification=STRING
    ),
    "AttackPattern": dict(
        Node,
        created_by_ref=STRING,
        external_references=STRING,
        kill_chain_phases=STRING,
        labels=STRING,
        modified=STRING,
        name=STRING,
        source=STRING,
        type=STRING
    ),
    "Campaign": dict(
        Node,
        created_by_ref=STRING,
        aliases=STRING,
        kill_chain_phases=STRING,
        labels=STRING,
        first_seen=DATETIME,
        last_seen=DATETIME,
        modified=DATETIME,
        name=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        objective=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "CourseOfAction": dict(
        Node,
        created_by_ref=STRING,
        action=STRING,
        labels=STRING,
        modified=DATETIME,
        name=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING
    ),
    "Identity": dict(
        Node,
        created_by_ref=STRING,
        contact_information=STRING,
        labels=STRING,
        identity_class=STRING,
        modified=DATETIME,
        name=STRING,
        sectors=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING
    ),
    "Indicator": dict(
        Node,
        created_by_ref=STRING,
        kill_chain_phases=STRING,
        labels=STRING,
        identity_class=STRING,
        modified=DATETIME,
        name=STRING,
        pattern=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        valid_from=DATETIME,
        valid_until=DATETIME
    ),
    "IntrusionSet": dict(
        Node,
        aliases=STRING,
        created_by_ref=STRING,
        first_seen=DATETIME,
        last_seen=DATETIME,
        labels=STRING,
        goals=STRING,
        modified=DATETIME,
        name=STRING,
        primary_motivation=STRING,
        resource_level=STRING,
        secondary_motivations=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "Malware": dict(
        Node,
        created_by_ref=STRING,
        labels=STRING,
        kill_chain_phases=STRING,
        modified=DATETIME,
        name=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING
    ),
    "ObservedData": dict(
        Node,
        created_by_ref=STRING,
        first_observed=DATETIME,
        last_observed=DATETIME,
        labels=STRING,
        number_observed=STRING,
        modified=DATETIME,
        name=STRING,
        objects=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "Report": dict(
        Node,
        created_by_ref=STRING,
        labels=STRING,
        modified=DATETIME,
        name=STRING,
        object_refs=STRING,
        published=DATETIME,
        source=STRING,
        type=STRING,
        revoked=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "Sighting": dict(
        Node,
        count=STRING,
        created_by_ref=STRING,
        first_seen=DATETIME,
        last_seen=DATETIME,
        labels=STRING,
        number_observed=STRING,
        modified=DATETIME,
        observed_data_refs=STRING,
        sighting_of_ref=STRING,
        summary=STRING,
        where_sighted_refs=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "ThreatActor": dict(
        Node,
        aliases=STRING,
        created_by_ref=STRING,
        first_seen=DATETIME,
        last_seen=DATETIME,
        labels=STRING,
        goals=STRING,
        modified=DATETIME,
        name=STRING,
        personal_motivations=STRING,
        primary_motivation=STRING,
        resource_level=STRING,
        sophistication=STRING,
        secondary_motivations=STRING,
        source=STRING,
        type=STRING,
        revoked=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "Tool": dict(
        Node,
        created_by_ref=STRING,
        kill_chain_phases=STRING,
        labels=STRING,
        modified=DATETIME,
        name=STRING,
        revoked=STRING,
        source=STRING,
        tool_version=STRING,
        type=STRING,

    ),
    "Vulnerability": dict(
        Node,
        created_by_ref=STRING,
        labels=STRING,
        modified=DATETIME,
        name=STRING,
        revoked=STRING,
        source=STRING,
        type=STRING,
    ),
    "Process": dict(
        Node,
        category=STRING,
        name=STRING,
        started=DATETIME,
        ended=DATETIME,
        pid=STRING,
        summary=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "Monitor": dict(
        Node,
        user=STRING,
        name=STRING,
        searchValue=STRING,
        type=STRING,
    ),
    "User": dict(
        Node,
        userName=STRING
    )}

UserModel = {
    "User": dict(
        Node,
        userName=STRING,
        passWord=STRING,
        email=STRING,
        MidName=STRING,
        Gender=STRING
    ),
    "Message": dict(
        Node,
        text=STRING,
        tags=STRING,
        sender=STRING,
        receiver=STRING,
        createDate=DATETIME
    ),
    "Session": dict(
        Node,
        startDate=DATETIME,
        endDate=DATETIME,
        user=STRING,
        ipAddress=STRING,
        token=STRING
    ),
    "Blacklist": dict(
        Node,
        createDate=DATETIME,
        user=STRING,
        ipAddress=STRING,
        token=STRING,
        session=STRING,
    )

}

POLEModel = {
    "Person": dict(
        Node,
        DateOfBirth=DATETIME,
        PlaceOfBirth=STRING,
        FirstName=STRING,
        LastName=STRING,
        MidName=STRING,
        Gender=STRING
    ),
    "Object": dict(
        Node,
        Category=STRING,
        Tags=STRING
    ),
    "Location": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        Latitude=FLOAT,
        Longitude=FLOAT,
        city=STRING,
        pop=INTEGER,
        country=STRING,
        iso3=STRING,
        province=STRING
    ),
    "Event": dict(
        Node,
        Category=STRING,
        Tags=STRING,
        StartDate=DATETIME,
        EndDate=DATETIME
    ),
    "BaseNames": dict(
        Node,
        Name=STRING,
        NameType=STRING,
        NameOrigin=STRING
    ),
    "Case": dict(
        Node,
        Name=STRING,
        Owners=STRING,
        StartDate=DATETIME,
        LastUpdate=DATETIME,
        CreatedBy=STRING,
        Members=STRING,
        Classification=STRING
    )
}

