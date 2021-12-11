import QtQuick 2.15
import QtQuick.Controls 2.15

ScrollView {
    width: 200
    height: 200
    clip: true
    anchors.fill: parent
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    Label {
        text: explore_backend.categories.forYou[0].title
        font.pixelSize: 26
        color: "red"
    }
}
