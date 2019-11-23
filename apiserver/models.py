"""
Central management for models.
TODO surface for UI configuration

"""
OSINTModel = {
            "Person": {
                "key": "integer",
                "hash": "string",
                "DateOfBirth": "datetime",
                "PlaceOfBirth": "string",
                "FirstName": "string",
                "LastName": "string",
                "MidName": "string",
                "icon": "string",
                "Gender": "string",
                "class": "V"
            },
            "Object": {
                "key": "integer",
                "hash": "string",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "icon": "string",
                "title": "string",
            },
            "Organization": {
                "key": "integer",
                "hash": "string",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Members": "integer",
                "Founded": "datetime",
                "Name": "string",
                "OtherNames": "string",
                "UCDP_id": "string",
                "ACLED_id": "string",
                "Source": "string",
                "icon": "string",
                "title": "string",
            },
            "Profile": {
                "key": "integer",
                "hash": "string",
                "class": "V",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Friends": "integer",
                "Followers": "integer",
                "Name": "string",
                "OtherNames": "string",
                "Posts": "integer",
                "DateCreated": "datetime",
                "url": "string",
                "Source": "string",
                "icon": "string",
                "title": "string",
            },
            "Post": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "DateCreated": "datetime",
                "RePosts": "integer",
                "Likes": "integer",
                "Author": "string",
                "url": "string",
                "Source": "string",
                "icon": "string",
                "title": "string",
            },
            "Location": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Latitude": "float",
                "Longitude": "float",
                "city": "string",
                "pop": "integer",
                "country": "string",
                "iso3": "string",
                "province": "string",
                "icon": "string",
                "title": "string",
            },
            "Event": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "StartDate": "datetime",
                "EndDate": "datetime",
                "icon": "string",
                "title": "string",
                "Sources": "string",
                "Deaths": "string",
                "Civilians": "string",
                "Origin": "string",
                "UCDP_id": "string",
                "Source": "string"
            },
            "Case": {
                "key": "string",
                "class": "V",
                "hash": "string",
                "Name": "string",
                "Owners": "string",
                "Classification": "string",
                "StartDate": "datetime",
                "LastUpdate": "datetime",
                "CreatedBy": "string",
                "Members": "string"
            }
        }

UserModel = {
            "User": {
                "key": "integer",
                "createDate": "datetime",
                "userName": "string",
                "passWord": "string",
                "email": "string",
                "icon": "string",
                "confirmed": "boolean",
                "class": "V"
            },
            "Message": {
                "key": "integer",
                "class": "V",
                "text": "string",
                "title": "string",
                "tags": "string",
                "sender": "string",
                "receiver": "string",
                "icon": "string",
                "createDate": "datetime"
            },
            "Session": {
                "key": "integer",
                "user": "string",
                "startDate": "datetime",
                "endDate": "datetime",
                "ipAddress": "string",
                "token": "string",
                "icon": "string",
                "class": "V"
            },
            "Blacklist": {
                "key": "integer",
                "token": "string",
                "user": "string",
                "session": "string",
                "createDate": "string",
                "icon": "string",
                "class": "V"
            }
        }

POLEModel = {
            "Person": {
                "key": "integer",
                "hash": "string",
                "DateOfBirth": "datetime",
                "PlaceOfBirth": "string",
                "FirstName": "string",
                "LastName": "string",
                "MidName": "string",
                "icon": "string",
                "Gender": "string",
                "class": "V"
            },
            "Object": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string"
            },
            "Location": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "Latitude": "float",
                "Longitude": "float",
                "city": "string",
                "pop": "integer",
                "country": "string",
                "iso3": "string",
                "province": "string"
            },
            "Event": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Category": "string",
                "Description": "string",
                "Tags": "string",
                "StartDate": "datetime",
                "EndDate": "datetime"
            },
            "BaseNames": {
                "key": "integer",
                "class": "V",
                "hash": "string",
                "Name": "string",
                "NameType" : "string",
                "NameOrigin": "string"
            },
            "Case": {
                "key": "string",
                "class": "V",
                "Name": "string",
                "hash": "string",
                "Owners": "string",
                "Classification": "string",
                "StartDate": "datetime",
                "LastUpdate": "datetime",
                "CreatedBy": "string",
                "Members": "string"
            }
        }
