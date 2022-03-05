import QtQuick 2.15
import QtQuick.Layouts 1.15
import Qt.labs.qmlmodels 1.0
import QtQuick.Controls 2.15


ColumnLayout {
    width: 500
    height: 600
    spacing: 2

    Rectangle {
        Layout.alignment: Qt.AlignTop
        color: "transparent"
        Layout.fillWidth: true
        Layout.preferredHeight: 100

        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            border.color: "#d0d0d0"
            border.width: 2
            radius: 10
            color: "transparent"

            DropArea {
                anchors.fill: parent

                onEntered: function (dropEvent) {
                    if (!dropEvent.hasUrls || dropEvent.urls.length == 0) {
                        dropEvent.accept(Qt.IgnoreAction)
                        return
                    }
                    dropEvent.accept(Qt.LinkAction)
                }

                onDropped: function (dropEvent) {
                    if (!dropEvent.hasUrls || dropEvent.urls.length == 0) {
                        dropEvent.accept(Qt.IgnoreAction)
                        return
                    }
                    if (!backend.filesDropped(dropEvent.urls)) {
                        dropEvent.accept(Qt.IgnoreAction)
                        return
                    }
                    dropEvent.accept(Qt.LinkAction)
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                text: "将文件或目录拖放到这里选择文件"
                font.pointSize: 16
                font.bold: true
                color: "#c0c0c0"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: 40
        spacing: 2

        Button {
            text: "上传"
            onClicked: backend.upload()
        }

        Button {
            text: "清空"
            onClicked: backend.clearAll()
        }
    }

    HorizontalHeaderView {
        syncView: uploadingView
        Layout.fillWidth: true
        Layout.preferredHeight: 20
        model: backend ? backend.uploading_song_model : null
    }

    TableView {
        id: uploadingView
        Layout.alignment: Qt.AlignTop
        Layout.fillWidth: true
        Layout.preferredHeight: 500
        Layout.fillHeight: true
        columnSpacing: 0
        rowSpacing: 0
        clip: true

        property var columnWidths: [420, 80]
        columnWidthProvider: function (column) { return columnWidths[column] }
        model: backend ? backend.uploading_song_model : null

        delegate: Rectangle {
            implicitHeight: 20
            clip: true
            Text {
              text: display
              color: "#444444"
              font.pointSize: 10
              anchors.left: parent.left
              anchors.leftMargin: 2
              anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}