import requests
import json
import math
import pandas as pd


def listWidgets( mural_id, auth_token, next_token ):
    # https://developers.mural.co/public/reference/getmuralwidgets
    url = "https://app.mural.co/api/public/v1/murals/" + mural_id + "/widgets"
    if next_token:
        url += "?next=" + next_token
    headers = { "Accept": "application/json", "Authorization": "Bearer " + auth_token }
    response = requests.request( "GET", url, headers = headers )
    response_json = json.loads( response.text )
    msg = ""
    if "code" in response_json:
        msg += response_json["code"] + " "
    if "message" in response_json:
        msg += response_json["message"]
    if msg != "":
        print( msg )
        return { "value" : [] }
    if "value" not in response_json:
        print( "No value returned" )
        return { "value" : [] }
    return response_json


def listAllWidgets( mural_id, auth_token ):
    all_results = []
    response_json = listWidgets( mural_id, auth_token, None )
    all_results += response_json["value"]
    while "next" in response_json:
        response_json = listWidgets( mural_id, auth_token, response_json["next"] )
        all_results += response_json["value"]
    return all_results


def getWidget( widget_id_in, widgets_arr ):
    for widget in widgets_arr:
        if widget["id"] == widget_id_in:
            return widget
    return None


def getParentOffset( parent_id, widgets_arr ):
    offset = { "x" : 0, "y" : 0 }
    parent_widget = getWidget( parent_id, widgets_arr )
    if None != parent_widget:
        offset["x"] += parent_widget["x"]
        offset["y"] += parent_widget["y"]
        # Now recurse, in case the parent has a parent...
        parent_offset = getParentOffset( parent_widget["parentId"], widgets_arr )
        offset["x"] += parent_offset["x"]
        offset["y"] += parent_offset["y"]
    return offset 


def getCircles( mural_id, auth_token ):
    widgets_arr = listAllWidgets( mural_id, auth_token )
    if len( widgets_arr ) < 1:
        print( "Failed to find widgets in the mural" )
        return None
    circles_arr = []
    for widget in widgets_arr:
        if( "shape" not in widget ) or ( "circle" != widget["shape"] ):
            continue
        parent_offset = getParentOffset( widget["parentId"], widgets_arr )
        x = widget["x"] + parent_offset["x"]
        y = widget["y"] + parent_offset["y"]
        radius = 0.5 * widget["width"];
        center_x = x + radius;
        center_y = y + radius;
        circles_arr.append( { "id" : widget["id"],
                               "x" : x,
                               "y" : y,
                               "center_x" : center_x,
                               "center_y" : center_y,
                               "radius"   : radius
                             } )
    return circles_arr


def biggestCircle( circles_arr ):
    biggest_radius = 0
    biggest_circle = None
    for circle in circles_arr:
        if circle["radius"] > biggest_radius:
            biggest_radius = circle["radius"]
            biggest_circle = circle
    return biggest_circle


def calcDistance( x1, y1, x2, y2 ):
    distance_x = abs( x2 - x1 )
    distance_y = abs( y2 - y1 )
    distance   = math.sqrt( distance_x**2 + distance_y**2 )
    return distance


def pointIsInsideCircle( x, y, circle ):
    distance_center = calcDistance( x, y, circle["center_x"], circle["center_y"] )
    if distance_center < circle["radius"]:
        return True
    return False


def getRadarCircles( mural_id, auth_token ):
    circles_arr = getCircles( mural_id, auth_token )
    if None == circles_arr:
        return None
    biggest_circle = biggestCircle( circles_arr )
    radar_circles = [ biggest_circle ]
    for circle in circles_arr:
        if circle["id"] == biggest_circle["id"]:
            continue
        if pointIsInsideCircle( circle["center_x"], circle["center_y"], biggest_circle ):
            radar_circles.append( circle )
    radar_circles = sorted( radar_circles, key=lambda x: x["radius"], reverse=True )
    radar_circles.pop(); # Smallest one is just labels
    return radar_circles


def printRadarCircles( radar_circles ):
    for circle in radar_circles:
        txt = circle["id"].ljust(18) + \
              " (" + \
              " [ " + str( round( circle["center_x"] ) ) + ", " + str( round( circle["center_y"] ) ) + " ]" + \
              " radius: " + str( round( circle["radius"] ) ) + \
              " )"
        print( txt )


def getArrows( mural_id, auth_token ):
    widgets_arr = listAllWidgets( mural_id, auth_token )
    if len( widgets_arr ) < 1:
        print( "Failed to find widgets in the mural" )
        return None
    arrows_arr = []
    for widget in widgets_arr:
        if ( "arrowType" not in widget ) or ( "straight" != widget["arrowType"] ) or ( "no tip" != widget["tip"] ):
            continue;
        parent_offset = getParentOffset( widget["parentId"], widgets_arr )
        x = widget["x"] + parent_offset["x"]
        y = widget["y"] + parent_offset["y"]
        length = math.sqrt( widget["width"]**2 + widget["height"]**2 );
        x1 = x + widget["points"][0]["x"];
        y1 = y + widget["points"][0]["y"];
        x2 = x + widget["points"][1]["x"];
        y2 = y + widget["points"][1]["y"];
        arrows_arr.append( { "id" : widget["id"],
                             "x1" : x1,
                             "y1" : y1,
                             "x2" : x2,
                             "y2" : y2,
                             "length" : length
                            } )
    return arrows_arr


def getRadarAngle(  center_x, center_y, x, y ):
    # Imagine: a line from the center of a circle, at [ center_x, center_y ], 
    # to a point on the circumfrence of the circle, at [ x, y ].
    # Measure the angle from the virtical.  
    # (eg. At 3:00PM, the hour hand is +90 degrees)
    #
    return -1 * ( ( math.atan2( x - center_x, y - center_y ) * 180 / math.pi ) - 180 );


def getRadarLines( mural_id, auth_token, radar_circles ):
    arrows_arr = getArrows( mural_id, auth_token )
    if None == arrows_arr:
        return None
    radar_lines_arr = []
    circle = radar_circles[0]
    for arrow in arrows_arr:
        if pointIsInsideCircle( arrow["x1"], arrow["y1"], circle ) or pointIsInsideCircle( arrow["x2"], arrow["y2"], circle ):
            center_x = arrow["x1"] if ( abs( circle["center_x"] - arrow["x1"] ) < abs( circle["center_x"] - arrow["x2"] ) ) else arrow["x2"]
            center_y = arrow["y1"] if ( abs( circle["center_y"] - arrow["y1"] ) < abs( circle["center_y"] - arrow["y2"] ) ) else arrow["y2"]
            x = arrow["x2"] if ( abs( circle["center_x"] - arrow["x1"] ) < abs( circle["center_x"] - arrow["x2"] ) ) else arrow["x1"]
            y = arrow["y2"] if ( abs( circle["center_y"] - arrow["y1"] ) < abs( circle["center_y"] - arrow["y2"] ) ) else arrow["y1"]
            angle = getRadarAngle( center_x, center_y, x, y )
            arrow["angle"] = angle
            radar_lines_arr.append( arrow )
    radar_lines_arr = sorted( radar_lines_arr, key=lambda x: x["angle"] )
    return radar_lines_arr


def printRadarLines( radar_lines ):
    for line in radar_lines:
        print( line["id"].ljust(18) + "( angle: " + str( round( line["angle"] ) ).ljust(3) + " )")


def getStickies( mural_id, auth_token ):
    widgets_arr = listAllWidgets( mural_id, auth_token )
    if len( widgets_arr ) < 1:
        print( "Failed to find widgets in the mural" )
        return None
    stickies_arr = []
    for widget in widgets_arr:
        if "sticky note" != widget["type"]:
            continue
        parent_offset = getParentOffset( widget["parentId"], widgets_arr )
        x = widget["x"] + parent_offset["x"]
        y = widget["y"] + parent_offset["y"]
        width    = widget["width"]
        height   = widget["height"]
        center_x = x + 0.5 * width
        center_y = y + 0.5 * height
        stickies_arr.append( { "id" : widget["id"],
                               "x"  : x,
                               "y"  : y,
                               "width"    : width,
                               "height"   : height,
                               "center_x" : center_x,
                               "center_y" : center_y,
                               "text"     : widget["text"],
                               "bg_color" : widget["style"]["backgroundColor"]
                             } )
    return stickies_arr


def addStickyRadarCircleIndex( stickies_arr, radar_circles ):
    for sticky in stickies_arr:
        distance = calcDistance( sticky["center_x"], sticky["center_y"], radar_circles[0]["center_x"], radar_circles[0]["center_y"] )
        if distance < radar_circles[2]["radius"]:
            sticky["radar_circle_index"] = 0
        elif distance < radar_circles[1]["radius"]:
            sticky["radar_circle_index"] = 1
        elif distance < radar_circles[0]["radius"]:
            sticky["radar_circle_index"] = 2


def addStickyRadarZoneIndex( stickies_arr, circle, radar_lines ):
    for sticky in stickies_arr:
        if "radar_circle_index" in sticky:
            sticky_angle = getRadarAngle( circle["center_x"], circle["center_y"], sticky["center_x"], sticky["center_y"] )
            sticky["radar_angle_index"] = len( radar_lines ) - 1
            for i in range( len( radar_lines ) - 1 ):
                if sticky_angle < radar_lines[i+1]["angle"]:
                    sticky["radar_angle_index"] = i
                    break


def getRadarStickies( mural_id, auth_token, radar_circles, radar_lines ):
    stickies_arr = getStickies( mural_id, auth_token )
    if None == stickies_arr:
        return None
    addStickyRadarCircleIndex( stickies_arr, radar_circles )
    addStickyRadarZoneIndex( stickies_arr, radar_circles[0], radar_lines )
    radar_stickies = []
    for sticky in stickies_arr:
        if "radar_circle_index" in sticky:
            radar_stickies.append( sticky )
    return radar_stickies


def resultsDataframe( radar_stickies ):
    angles_titles_arr = [ "MORE OF    ", 
                          "START DOING", 
                          "STOP DOING ",
                          "LESS OF    ",
                          "KEEP DOING "
                        ]
    circles_titles_arr = [ "CONTROL  ",
                           "INFLUENCE",
                           "CONCERN  "
                         ]
    #results = [ [ "", 0, "MORE OF",     0, "CONTROL",   "" ],
    #            [ "", 1, "START DOING", 1, "INFLUENCE", "" ],
    #            [ "", 2, "STOP DOING",  2, "CONCERN",   "" ],
    #            [ "", 3, "LESS OF",     2, "CONCERN",   "" ],
    #            [ "", 4, "KEEP DOING",  2, "CONCERN",   "" ]
    #          ]
    results = []
    for sticky in radar_stickies: 
        results.append( [ sticky["id"],
                          sticky["radar_angle_index"],
                          angles_titles_arr[ sticky["radar_angle_index"] ],
                          sticky["radar_circle_index"],
                          circles_titles_arr[ sticky["radar_circle_index"] ],
                          sticky["text"] ] )
    df = pd.DataFrame( results, columns=[ "STICKY ID", "STARFISH INDEX", "STARFISH ZONE", "CIRCLE INDEX", "CIRCLE OF CONTROL", "TEXT" ] )
    return df

