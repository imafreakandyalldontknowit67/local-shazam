const std = @import("std");
const Io = std.Io;

const REF_FILES = [_][]const u8{
    "1051039.mp3",
    "1071559.mp3",
    "1075784.mp3",
    "11266.mp3",
    "147199.mp3",
    "173050.mp3",
    "189211.mp3",
    "297888.mp3",
    "612409.mp3",
    "852601.mp3",
};
const REF_TARGET_FOLDER = "dataset/ref";

const QUERY_FILES = [_][]const u8{
    "1024035_55s-75s.mp3",
    "1051039_34s-54s.mp3",
    "1071559_60s-80s.mp3",
    "1075784_78s-98s.mp3",
    "11266_69s-89s.mp3",
    "132755_137s-157s.mp3",
    "147199_115s-135s.mp3",
    "173050_86s-106s.mp3",
    "189211_60s-80s.mp3",
    "295781_88s-108s.mp3",
    "297888_45s-65s.mp3",
    "361430_180s-200s.mp3",
    "371009_187s-207s.mp3",
    "378501_59s-79s.mp3",
    "384991_294s-314s.mp3",
    "432279_81s-101s.mp3",
    "43383_224s-244s.mp3",
    "478466_24s-44s.mp3",
    "602848_242s-262s.mp3",
    "604705_154s-174s.mp3",
    "612409_73s-93s.mp3",
    "824093_182s-202s.mp3",
    "84302_232s-252s.mp3",
    "852601_43s-63s.mp3",
    "96644_84s-104s.mp3",
};
const QUERY_TARGET_FOLDER = "dataset/queries";

const QUERY_OTA_FILES = [_][]const u8{
    "1024035_55s-75s_ota.mp3",
    "1051039_34s-54s_ota.mp3",
    "1071559_60s-80s_ota.mp3",
    "1075784_78s-98s_ota.mp3",
    "11266_69s-89s_ota.mp3",
    "132755_137s-157s_ota.mp3",
    "147199_115s-135s_ota.mp3",
    "173050_86s-106s_ota.mp3",
    "189211_60s-80s_ota.mp3",
    "295781_88s-108s_ota.mp3",
    "297888_45s-65s_ota.mp3",
    "361430_180s-200s_ota.mp3",
    "371009_187s-207s_ota.mp3",
    "378501_59s-79s_ota.mp3",
    "384991_294s-314s_ota.mp3",
    "432279_81s-101s_ota.mp3",
    "43383_224s-244s_ota.mp3",
    "478466_24s-44s_ota.mp3",
    "602848_242s-262s_ota.mp3",
    "604705_154s-174s_ota.mp3",
    "612409_73s-93s_ota.mp3",
    "824093_182s-202s_ota.mp3",
    "84302_232s-252s_ota.mp3",
    "852601_43s-63s_ota.mp3",
    "96644_84s-104s_ota.mp3",
};
const QUERY_OTA_TARGET_FOLDER = "dataset/queries_ota";

pub const DatasetKind = enum {
    ref_only,
    ref_and_queries,
    all, // includes OTA queries
};

/// Release override: fixtures must be supplied explicitly; never use the network.
/// Missing fixtures are errors, not an assertion that dataset tests passed.
pub fn ensureDataset(io: Io, allocator: std.mem.Allocator, kind: DatasetKind) !void {
    try checkFiles(io, allocator, REF_TARGET_FOLDER, &REF_FILES, 100 * 1024);
    if (kind == .ref_only) return;
    try checkFiles(io, allocator, QUERY_TARGET_FOLDER, &QUERY_FILES, 100 * 1024);
    if (kind == .ref_and_queries) return;
    try checkFiles(io, allocator, QUERY_OTA_TARGET_FOLDER, &QUERY_OTA_FILES, 50 * 1024);
}

fn checkFiles(io: Io, allocator: std.mem.Allocator, folder: []const u8, files: []const []const u8, min_size: u64) !void {
    for (files) |file| {
        const path = try std.fmt.allocPrint(allocator, "{s}/{s}", .{ folder, file });
        defer allocator.free(path);
        const stat = Io.Dir.cwd().statFile(io, path, .{}) catch {
            std.debug.print("Missing audio fixture {s}; no download attempted. See BUILDING.md.\n", .{path});
            return error.MissingAudioFixture;
        };
        if (stat.size < min_size) {
            std.debug.print("Invalid audio fixture {s}: {d} bytes\n", .{ path, stat.size });
            return error.InvalidAudioFixture;
        }
    }
}
