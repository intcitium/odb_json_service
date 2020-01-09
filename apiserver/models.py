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
Edge = {
    "class": "E",
    "out": "Link",
    "in": "Link"
    }
Node = {"class": "V",
        "Ext_key": STRING,
        "hashkey": STRING,
        "description": STRING,
        "icon": STRING,
        "title": STRING
        }

Edges = {
    "Discovered": Edge, "Has": Edge, "Included": Edge, "Initiated": Edge,
    "LocatedAt": Edge, "Owns": Edge, "Received": Edge, "References": Edge,
    "Tweeted": Edge, "TweetedFrom": Edge}

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
        objective=STRING
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
        valid_until=DATETIME,
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
        revoked=STRING
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
        revoked=STRING
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
        revoked=STRING
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
        revoked=STRING
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
        revoked=STRING
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
        summary=STRING
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
    ),
}

UserModel = {
            "User": {
                "createDate": "datetime",
                "userName": "string",
                "passWord": "string",
                "email": "string",
                "icon": "string",
                "confirmed": "boolean",
                "class": "V",
                "hashkey": "string"
            },
            "Message": {
                "class": "V",
                "text": "string",
                "title": "string",
                "tags": "string",
                "sender": "string",
                "receiver": "string",
                "icon": "string",
                "createDate": "datetime",
                "hashkey": "string"
            },
            "Session": {
                "user": "string",
                "startDate": "datetime",
                "endDate": "datetime",
                "ipAddress": "string",
                "token": "string",
                "icon": "string",
                "class": "V",
                "hashkey": "string"
            },
            "Blacklist": {
                "token": "string",
                "user": "string",
                "session": "string",
                "createDate": "string",
                "icon": "string",
                "class": "V",
                "hashkey": "string"
            }
        }

POLEModel = {
            "Person": {
                "key": "integer",
                "DateOfBirth": "datetime",
                "PlaceOfBirth": "string",
                "FirstName": "string",
                "LastName": "string",
                "MidName": "string",
                "icon": "string",
                "Gender": "string",
                "class": "V",
                "hashkey": "string"
            },
            "Object": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "description": "string",
                "Tags": "string",
                "hashkey": "string"
            },
            "Location": {
                "key": "integer",
                "class": "V",
                "Category": "string",
                "description": "string",
                "Tags": "string",
                "Latitude": "float",
                "Longitude": "float",
                "city": "string",
                "pop": "integer",
                "country": "string",
                "iso3": "string",
                "province": "string",
                "hashkey": "string"
            },
            "Event": {
                "class": "V",
                "Category": "string",
                "description": "string",
                "Tags": "string",
                "StartDate": "datetime",
                "EndDate": "datetime",
                "hashkey": "string"
            },
            "BaseNames": {
                "class": "V",
                "Name": "string",
                "NameType" : "string",
                "NameOrigin": "string",
                "hashkey": "string"
            },
            "Case": {
                "class": "V",
                "Name": "string",
                "Owners": "string",
                "Classification": "string",
                "StartDate": "datetime",
                "LastUpdate": "datetime",
                "CreatedBy": "string",
                "Members": "string",
                "hashkey": "string",
                "description": "string"
            }
        }
