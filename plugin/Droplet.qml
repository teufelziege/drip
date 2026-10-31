import QtQuick
import qs.Commons as Commons
Item {
    id: root
    property color tint: Commons.Color.accent
    property bool happy: false
    property bool dancing: false
    readonly property bool danceEnabled: dancing && visible && !Commons.Style.reduceMotion
    onDanceEnabledChanged: if (!danceEnabled) { art.rotation = 0; art.y = 0 }
    SequentialAnimation {
        running: root.danceEnabled
        loops: Animation.Infinite
        NumberAnimation { target: art; property: "rotation"; from: 0; to: -13; duration: Commons.Style.duration(180); easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "rotation"; from: -13; to: 13; duration: Commons.Style.duration(240); easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "rotation"; from: 13; to: 0; duration: Commons.Style.duration(180); easing.type: Easing.OutCubic }
    }
    SequentialAnimation {
        running: root.danceEnabled
        loops: Animation.Infinite
        NumberAnimation { target: art; property: "y"; from: 0; to: -2; duration: Commons.Style.duration(150); easing.type: Easing.OutCubic }
        NumberAnimation { target: art; property: "y"; from: -2; to: 0; duration: Commons.Style.duration(150); easing.type: Easing.OutCubic }
    }
    implicitWidth: 25
    implicitHeight: 29
    Canvas {
        id: art
        width: parent.width; height: parent.height
        transformOrigin: Item.Bottom
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: root; function onTintChanged() { art.requestPaint() } function onHappyChanged() { art.requestPaint() } }
        onPaint: {
            var c = getContext("2d"); c.reset(); c.scale(width/32, height/38)
            c.beginPath(); c.moveTo(16,1); c.bezierCurveTo(12,9,2,17,2,24); c.bezierCurveTo(2,42,30,42,30,24); c.bezierCurveTo(30,17,20,9,16,1)
            c.fillStyle=root.tint; c.fill()
            c.fillStyle=Qt.rgba(1,1,1,0.55); c.beginPath(); c.ellipse(7,16,4,8); c.fill()
            c.fillStyle=Commons.Color.background
            c.beginPath(); c.ellipse(10,23,2,3); c.ellipse(21,23,2,3); c.fill()
            c.lineWidth=1.5; c.strokeStyle=Commons.Color.background; c.beginPath(); c.arc(17,27,3,0,Math.PI); c.stroke()
            c.fillStyle=Qt.rgba(1,0.5,0.65,0.6); c.beginPath(); c.ellipse(6,28,4,2); c.ellipse(23,28,4,2); c.fill()
        }
    }
}
