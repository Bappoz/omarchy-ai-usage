import QtQuick
import QtQuick.Controls as Controls

Controls.Button {
  id: root
  property real uiScale: 1
  implicitHeight: 28 * uiScale
  implicitWidth: label.implicitWidth + 16 * uiScale
  padding: 6 * uiScale
  opacity: enabled ? 1 : 0.35
  background: Rectangle {
    radius: 7 * root.uiScale
    color: root.down ? "#383838" : (root.hovered ? "#303030" : "#202020")
    border.width: root.visualFocus ? 1 : 0
    border.color: "#808080"
  }
  contentItem: Text {
    id: label
    text: root.text
    color: "#ffffff"
    font.pixelSize: 10 * root.uiScale
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
    textFormat: Text.PlainText
  }
}
