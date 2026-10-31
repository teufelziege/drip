#include <QCoreApplication>
#include <QDateTime>
#include <QDirIterator>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLockFile>
#include <QSaveFile>
#include <QTextStream>
#include <cmath>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const auto args = app.arguments();
    auto option = [&](QString key, QString fallback) {
        int i = args.indexOf(key); return i >= 0 && i+1 < args.size() ? args[i+1] : fallback;
    };
    const QString home = QDir::homePath();
    const QString sessions = option("--sessions", home + "/.codex/sessions");
    const QString statePath = option("--state", home + "/.local/state/drip/state.json");
    auto fail = [](QString message) { QTextStream(stderr) << message << '\n'; return 1; };
    if (!QDir(sessions).exists()) return fail("Local Codex session directory is unavailable.");
    QDir().mkpath(QFileInfo(statePath).absolutePath());
    QLockFile lock(statePath + ".lock");
    if (!lock.tryLock(1000)) return fail("Drip state is busy.");
    QJsonObject state;
    QFile input(statePath);
    if (input.exists()) {
        if (!input.open(QIODevice::ReadOnly)) return fail(input.errorString());
        QJsonParseError error;
        auto document = QJsonDocument::fromJson(input.readAll(), &error);
        if (error.error != QJsonParseError::NoError || !document.isObject()) return fail("Drip state is invalid; refusing to overwrite it.");
        state = document.object();
    }
    double rate = state.value("ml_per_prompt").toDouble(0.32);
    if (args.contains("--rate")) {
        bool ok = false;
        rate = option("--rate", "").toDouble(&ok);
        if (!ok || !std::isfinite(rate) || rate < 0 || rate > 10000) return fail("Rate must be between 0 and 10000 mL.");
    }
    QJsonObject offsets = state.value("offsets").toObject();
    QJsonObject events = state.value("events").toObject();
    QJsonObject active = state.value("active").toObject();
    // Replay once when upgrading so existing unfinished turns are discovered.
    if (state.value("activity_version").toInt() != 1) offsets = {};
    const auto today = QDate::currentDate();
    int unreadable = 0;
    // Old conversations can receive new turns, so discover all files but read only appended bytes.
    {
        QString folder = sessions;
        QDirIterator files(folder, {"*.jsonl"}, QDir::Files, QDirIterator::Subdirectories);
        while (files.hasNext()) {
            const QString path = files.next();
            QFile file(path);
            if (!file.open(QIODevice::ReadOnly)) { ++unreadable; continue; }
            qint64 offset = qint64(offsets.value(path).toDouble());
            if (offset > file.size()) offset = 0;
            if (!file.seek(offset)) { ++unreadable; continue; }
            while (!file.atEnd()) {
                qint64 start = file.pos();
                QByteArray line = file.readLine();
                if (!line.endsWith('\n')) { file.seek(start); break; }
                QJsonObject event = QJsonDocument::fromJson(line).object();
                if (event.value("type") != "event_msg") continue;
                auto payload = event.value("payload").toObject();
                auto attribution = payload.value("turn_attribution").toObject();
                QString activityId = payload.value("turn_id").toString();
                if (activityId.isEmpty()) activityId = attribution.value("turn_id").toString();
                const auto kind = payload.value("type").toString();
                if (kind == "task_complete" || kind == "turn_aborted" || kind == "task_aborted") {
                    if (!activityId.isEmpty()) active.remove(activityId);
                    else {
                        for (const auto &key : active.keys()) if (active.value(key).toString() == path) active.remove(key);
                    }
                }
                if (kind == "task_started" && attribution.value("turn_trigger") != "guardian_review" && !activityId.isEmpty()) active.insert(activityId, path);
                if (kind != "task_started" || attribution.value("turn_trigger") != "user") continue;
                if (!attribution.value("initiating_agent_path").isNull() && !attribution.value("initiating_agent_path").toString().isEmpty()) continue;
                QString id = payload.value("turn_id").toString();
                if (id.isEmpty()) id = attribution.value("turn_id").toString();
                auto timestamp = QDateTime::fromString(event.value("timestamp").toString(), Qt::ISODateWithMs);
                if (!id.isEmpty() && timestamp.isValid()) events.insert(id, timestamp.toMSecsSinceEpoch());
            }
            offsets.insert(path, double(file.pos()));
        }
    }
    int count = 0;
    qint64 last = 0;
    for (auto it = events.begin(); it != events.end(); ++it) {
        qint64 time = qint64(it.value().toDouble());
        if (QDateTime::fromMSecsSinceEpoch(time).date() == today) { ++count; last = qMax(last, time); }
    }
    int running = 0;
    for (const auto &key : active.keys()) {
        QFileInfo log(active.value(key).toString());
        // An abandoned session must not keep the animation running indefinitely.
        if (!log.exists() || log.lastModified().secsTo(QDateTime::currentDateTime()) > 300) active.remove(key);
        else ++running;
    }
    state.insert("active", active);
    state.insert("activity_version", 1);
    state.insert("events", events);
    state.insert("offsets", offsets);
    state.insert("ml_per_prompt", rate);
    QByteArray saved = QJsonDocument(state).toJson(QJsonDocument::Compact);
    QSaveFile output(statePath);
    if (!output.open(QIODevice::WriteOnly) || output.write(saved) != saved.size() || !output.commit()) return fail("Could not save Drip state.");
    QJsonObject result{{"prompts", count}, {"ml", count * rate}, {"rate", rate}, {"last", double(last)}, {"unreadable", unreadable}, {"estimated", true}, {"running", running}};
    QTextStream(stdout) << QJsonDocument(result).toJson(QJsonDocument::Compact) << '\n';
    return 0;
}
