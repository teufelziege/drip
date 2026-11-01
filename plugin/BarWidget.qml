import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons as Commons
BarWidget {
    id: root
    moduleName: "tlindsey.drip"
    implicitWidth: row.implicitWidth + 14
    implicitHeight: barSize
    property var stats: ({prompts: 0, ml: 0, rate: 0.32, last: 0})
    property bool failed: false
    property bool initialized: false
    property bool splash: false
    property bool pendingRefresh: false
    readonly property bool agentsRunning: !failed && (stats.running || 0) > 0
    readonly property bool opened: panel.open
    function open() { panel.open = true }
    function close() { panel.open = false }
    function refresh() { if (reader.running || adjustment.running) pendingRefresh = true; else reader.running = true }
    function drainRefresh() { if (pendingRefresh && !reader.running && !adjustment.running) { pendingRefresh = false; reader.running = true } }
    function volume(n) { return Commons.I18n.formatNumber(n, n < 10 ? 2 : 1) + " mL" }
    Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }
    Process {
        id: reader
        command: [Qt.resolvedUrl("drip").toString().replace(/^file:\/\//, "")]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var next = JSON.parse(text)
                    if (typeof next.prompts !== "number" || typeof next.ml !== "number") throw new Error("invalid")
                    if (root.initialized && next.last > root.stats.last) { root.splash = true; splashTimer.restart() }
                    root.stats = next; root.initialized = true; root.failed = false
                } catch (e) { root.failed = true }
            }
        }
        onExited: function(code) { if (code !== 0) root.failed = true; Qt.callLater(root.drainRefresh) }
    }
    Process {
        id: adjustment
        property real rate: 0.32
        command: [Qt.resolvedUrl("drip").toString().replace(/^file:\/\//, ""), "--rate", rate.toFixed(2)]
        onExited: { root.pendingRefresh = true; Qt.callLater(root.drainRefresh) }
    }
    Timer { interval: 3000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.refresh() }
    Timer { id: splashTimer; interval: 650; onTriggered: root.splash = false }
    Row {
        id: row; anchors.centerIn: parent; spacing: 7
        Droplet {
            anchors.verticalCenter: parent.verticalCenter; width: 21; height: 25
            dancing: root.agentsRunning && (!root.bar || !root.bar.barHidden)
            scale: root.splash ? 1.14 : 1
            Behavior on scale { NumberAnimation { duration: Commons.Style.duration(180); easing.type: Easing.OutCubic } }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.PlainText
            text: root.failed ? "Drip !" : "≈ " + root.volume(root.stats.ml)
            color: Commons.Color.foreground
            font.family: Commons.Style.font.family; font.pixelSize: Commons.Style.font.body
        }
    }
    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: panel.open = !panel.open }
    KeyboardPanel {
        id: panel
        bar: root.bar; anchorItem: root; owner: root
        contentWidth: 365; contentHeight: content.implicitHeight + verticalContentInset
        Column {
            id: content; width: parent.width; spacing: 12
            Text { width: parent.width; textFormat: Text.PlainText; text: strings.t("title"); color: Commons.Color.foreground; font.bold: true; font.pixelSize: 17 }
            Droplet { anchors.horizontalCenter: parent.horizontalCenter; width: 62; height: 74; dancing: root.agentsRunning && panel.open }
            Text { anchors.horizontalCenter: parent.horizontalCenter; textFormat: Text.PlainText; text: "≈ " + root.volume(root.stats.ml); color: Commons.Color.accent; font.bold: true; font.pixelSize: 30 }
            Text { anchors.horizontalCenter: parent.horizontalCenter; textFormat: Text.PlainText; text: strings.t("today"); color: Commons.Color.foreground }
            Rectangle {
                width: parent.width; height: 12; radius: 6; color: Qt.alpha(Commons.Color.accent, 0.15)
                Rectangle { width: Math.max(0, parent.width * Math.min(1, root.stats.ml / 250)); height: parent.height; radius: 6; color: Commons.Color.accent; Behavior on width { NumberAnimation { duration: Commons.Style.duration(180) } } }
            }
            Text { textFormat: Text.PlainText; text: strings.t("jar").arg(Commons.I18n.formatNumber(root.stats.ml / 2.5, 1)); color: Commons.Color.foreground }
            Text { textFormat: Text.PlainText; text: strings.tn("prompts", root.stats.prompts).arg(Commons.I18n.formatNumber(root.stats.prompts)); color: Commons.Color.foreground }
            Text { textFormat: Text.PlainText; text: strings.t("assumption").arg(Commons.I18n.formatNumber(root.stats.rate, 2)); color: Commons.Color.accent }
            Row {
                spacing: 10
                Button { text: strings.t("lower"); onClicked: { if (!adjustment.running) { adjustment.rate = Math.max(0, root.stats.rate - 0.1); adjustment.running = true } } }
                Button { text: strings.t("higher"); onClicked: { if (!adjustment.running) { adjustment.rate = root.stats.rate + 0.1; adjustment.running = true } } }
            }
            Text { width: parent.width; wrapMode: Text.WordWrap; textFormat: Text.PlainText; text: strings.t("note"); color: Commons.Color.foreground; font.pixelSize: 12 }
            Text { width: parent.width; wrapMode: Text.WordWrap; textFormat: Text.PlainText; text: strings.t("source"); color: Commons.Color.foreground; opacity: 0.7; font.pixelSize: 11 }
            Text { visible: root.failed || root.stats.unreadable > 0; width: parent.width; wrapMode: Text.WordWrap; textFormat: Text.PlainText; text: strings.t(root.failed ? "error" : "partial"); color: Commons.Color.accent }
        }
    }
}
