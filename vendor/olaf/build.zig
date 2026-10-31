const std = @import("std");

pub fn build(b: *std.Build) void {
    const release_privacy = b.option(bool, "release-privacy", "Compiler path privacy for release artifacts") orelse false;
    const privacy_cflags = b.option([]const u8, "privacy-cflags", "Generated Clang response file with file/macro/debug prefix maps");
    if (release_privacy and privacy_cflags == null) @panic("Release privacy requires explicit prefix maps");
    var artifacts = std.array_list.Managed(*std.Build.Step.Compile).init(b.allocator);
    defer if (release_privacy) {
        for (artifacts.items) |artifact| applyReleasePrivacy(b, artifact, privacy_cflags.?);
    };
    const cflags = [_][]const u8{ "-Wall", "-Wextra", "-Werror=return-type", "-std=gnu11", "-O2", "-fPIC" };

    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const build_core = b.option(bool, "core", "Build the Olaf core and not the CLI interface  (default: false)") orelse false;

    // The browser module (wasm/js/olaf.wasm), used by the demos in wasm/.
    const web = webModule(b);
    artifacts.append(web) catch @panic("OOM");
    const update_web = b.addUpdateSourceFiles();
    update_web.addCopyFileToSource(web.getEmittedBin(), "wasm/js/olaf.wasm");
    b.step("web", "Build the browser WebAssembly module into wasm/js/olaf.wasm").dependOn(&update_web.step);

    if (target.result.cpu.arch == .wasm32) {
        if (release_privacy) web.root_module.strip = true;
        b.installArtifact(web);
    } else {

        // if only build core c library olaf_core for linking from other languages
        if (build_core) {
            const exe = b.addExecutable(.{
                .name = "olaf_core",
                .root_module = b.createModule(.{
                    .target = target,
                    .optimize = optimize,
                }),
            });
            artifacts.append(exe) catch @panic("OOM");

            addCoreSources(exe, b, &cflags, true, true);
            exe.root_module.link_libc = true;
            // InstallArtifact snapshots PDB emission before the deferred privacy pass.
            if (release_privacy) exe.root_module.strip = true;
            b.installArtifact(exe);

            // run step
            const run_step = b.addRunArtifact(exe);
            run_step.setCwd(b.path(".")); // Set working directory to project root
            b.step("run", "Run Olaf core").dependOn(&run_step.step);

            if (b.args) |args| {
                run_step.addArgs(args);
            }
        } else {
            const exe = b.addExecutable(.{
                .name = "olaf",
                .root_module = b.createModule(.{
                    .target = target,
                    .optimize = optimize,
                    .root_source_file = b.path("./cli/olaf_cli.zig"),
                }),
            });
            artifacts.append(exe) catch @panic("OOM");
            exe.root_module.addIncludePath(b.path("cli"));
            exe.root_module.addIncludePath(b.path("src"));
            const zigzag = b.dependency("zigzag", .{ .target = target, .optimize = optimize });
            exe.root_module.addImport("zigzag", zigzag.module("zigzag"));
            // The REST API (cli/rest/) only depends on std; the CLI links it in.
            exe.root_module.addImport("olaf_rest", restModule(b, target, optimize));
            addCoreSources(exe, b, &cflags, true, false); // true = include LMDB sources
            exe.root_module.link_libc = true;
            // InstallArtifact snapshots PDB emission before the deferred privacy pass.
            if (release_privacy) exe.root_module.strip = true;
            b.installArtifact(exe);

            // run step
            const run_step = b.addRunArtifact(exe);
            run_step.setCwd(b.path(".")); // Set working directory to project root
            b.step("run", "Run Olaf CLI").dependOn(&run_step.step);

            if (b.args) |args| {
                run_step.addArgs(args);
            }
        }
    }

    const matcher_test = b.addExecutable(.{
        .name = "olaf_matcher_v3_tests",
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true }),
    });
    artifacts.append(matcher_test) catch @panic("OOM");
    matcher_test.root_module.addIncludePath(b.path("src"));
    matcher_test.root_module.addCSourceFiles(.{
        .files = &.{ "tests/olaf_matcher_v3_tests.c", "src/olaf_config.c", "src/hash-table.c" },
        .flags = &.{ "-std=gnu11", "-UNDEBUG" },
    });
    const matcher_step = b.step("test-matcher-v3", "Run isolated matcher voting and lookup boundary regressions");
    matcher_step.dependOn(&b.addRunArtifact(matcher_test).step);

    // Focused C regressions also run without audio tools or a dataset.
    const safety_step = b.step("test-db-safety", "Test fingerprint buffering and LMDB ownership");
    const writer_test = b.addExecutable(.{
        .name = "olaf_writer_safety",
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true }),
    });
    artifacts.append(writer_test) catch @panic("OOM");
    writer_test.root_module.addIncludePath(b.path("src"));
    writer_test.root_module.addCSourceFiles(.{
        .files = &.{ "tests/olaf_fp_db_writer_tests.c", "src/olaf_fp_db_writer.c" },
        .flags = &.{ "-std=gnu11", "-UNDEBUG" },
    });
    const run_writer = b.addRunArtifact(writer_test);
    safety_step.dependOn(&run_writer.step);

    const db_helper = b.addExecutable(.{
        .name = "olaf_db_concurrency",
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true }),
    });
    artifacts.append(db_helper) catch @panic("OOM");
    db_helper.root_module.addIncludePath(b.path("src"));
    db_helper.root_module.addCSourceFiles(.{
        .files = &.{ "tests/olaf_db_concurrency_tests.c", "src/olaf_db.c", "src/mdb.c", "src/midl.c" },
        .flags = &.{ "-std=gnu11", "-DOLAF_DB_TESTING", "-UNDEBUG" },
    });
    if (target.result.os.tag != .windows) db_helper.root_module.linkSystemLibrary("pthread", .{});
    const db_tests = b.addTest(.{
        .root_module = b.createModule(.{
            .target = target,
            .optimize = optimize,
            .root_source_file = b.path("tests/olaf_db_safety_tests.zig"),
        }),
    });
    artifacts.append(db_tests) catch @panic("OOM");
    const db_options = b.addOptions();
    db_options.addOptionPath("helper", db_helper.getEmittedBin());
    db_tests.root_module.addOptions("db_test_options", db_options);
    const run_db = b.addRunArtifact(db_tests);
    safety_step.dependOn(&run_db.step);

    const config_step = b.step("test-config-safety", "Test configuration bounds and constructor allocation failures");
    const config_test = b.addExecutable(.{
        .name = "olaf_config_safety",
        .root_module = b.createModule(.{ .target = target, .optimize = optimize, .link_libc = true }),
    });
    artifacts.append(config_test) catch @panic("OOM");
    config_test.root_module.addIncludePath(b.path("src"));
    config_test.root_module.addCSourceFile(.{ .file = b.path("tests/olaf_config_tests.c"), .flags = &.{ "-std=gnu11", "-DNDEBUG" } });
    const config_flags = &.{ "-std=gnu11", "-DNDEBUG", "-include", b.pathFromRoot("tests/olaf_config_alloc.h") };
    addCoreSources(config_test, b, config_flags, false, false);
    config_test.root_module.addCSourceFile(.{ .file = b.path("src/olaf_fft.c"), .flags = config_flags });
    b.step("check-config-safety", "Compile configuration regressions for the selected target").dependOn(&config_test.step);
    const run_config = b.addRunArtifact(config_test);
    run_config.addFileArg(b.path("tests/golden/output_snapshot.txt"));
    config_step.dependOn(&run_config.step);

    // Release source archives intentionally contain no audio. The broad suite
    // must not silently skip missing fixtures or download them on a build host.
    const test_step = b.step("test", "Run Olaf tests");
    const audio_tests = b.option(bool, "audio-tests", "Enable upstream tests with manually supplied audio fixtures (never downloaded)") orelse false;
    if (!audio_tests) {
        test_step.dependOn(&b.addFail("Audio fixtures are excluded from this source distribution. Use test-matcher-v3, test-db-safety or test-config-safety; see BUILDING.md before enabling -Daudio-tests=true.").step);
        return;
    }
    test_step.dependOn(matcher_step);
    test_step.dependOn(safety_step);
    test_step.dependOn(config_step);

    if (!build_core) {
        const test_files = [_][]const u8{
            "tests/olaf_unit_tests.zig",
            "tests/olaf_functional_tests.zig",
            // Core binding + session tests (config drift cross-check, store
            // equivalence) live in the cli module because tests/ files cannot
            // import across the module root.
            "cli/olaf_cli_session.zig",
            "cli/olaf_cli_threading.zig",
            "cli/olaf_cli_rest_client.zig",
            "cli/olaf_cli_rest_backend.zig",
            "cli/olaf_cli_has.zig",
            "cli/olaf_cli_help.zig",
            "cli/ui/olaf_ui.zig",
        };

        // The functional tests run the browser module in node.
        const web_options = b.addOptions();
        web_options.addOptionPath("wasm", web.getEmittedBin());

        // REST server, envelope and load balancer (std only, no C core).
        const rest_tests = b.addTest(.{ .root_module = restModule(b, target, optimize) });
        artifacts.append(rest_tests) catch @panic("OOM");
        test_step.dependOn(&b.addRunArtifact(rest_tests).step);

        for (test_files) |test_file| {
            const tests = b.addTest(.{
                .root_module = b.createModule(.{
                    .target = target,
                    .optimize = optimize,
                    .root_source_file = b.path(test_file),
                }),
            });
            artifacts.append(tests) catch @panic("OOM");

            tests.root_module.addIncludePath(b.path("cli"));
            tests.root_module.addIncludePath(b.path("src"));
            tests.root_module.addIncludePath(b.path("tests"));
            tests.root_module.addImport("olaf_rest", restModule(b, target, optimize));
            tests.root_module.addOptions("web_test_options", web_options);
            tests.root_module.addCSourceFile(.{ .file = b.path("tests/olaf_config_parity.c"), .flags = &cflags });
            addCoreSources(tests, b, &cflags, true, false);
            tests.root_module.link_libc = true;

            const run_tests = b.addRunArtifact(tests);
            run_tests.setCwd(b.path("."));
            // Functional tests shell out to the installed `olaf` binary.
            // Build+install it first and tell the test where to find it.
            run_tests.step.dependOn(b.getInstallStep());
            run_tests.setEnvironmentVariable("OLAF_BIN", b.getInstallPath(.bin, "olaf"));
            test_step.dependOn(&run_tests.step);
        }
    }
}

/// The "olaf_rest" module: the HTTP front end and load balancer in cli/rest/.
fn restModule(b: *std.Build, target: std.Build.ResolvedTarget, optimize: std.builtin.OptimizeMode) *std.Build.Module {
    return b.createModule(.{
        .target = target,
        .optimize = optimize,
        .root_source_file = b.path("cli/rest/olaf_rest.zig"),
        // listenExclusive uses the libc socket calls (POSIX).
        .link_libc = true,
    });
}

/// The browser module: a WASI reactor with the in-memory database. It exports
/// olaf_fingerprint_match, malloc and free; the match callback is imported
/// from JavaScript (see wasm/js/olaf_processor.js).
fn webModule(b: *std.Build) *std.Build.Step.Compile {
    const web = b.addExecutable(.{
        .name = "olaf",
        .root_module = b.createModule(.{
            .target = b.resolveTargetQuery(.{ .cpu_arch = .wasm32, .os_tag = .wasi }),
            .optimize = .ReleaseSmall,
            .link_libc = true,
            .strip = true,
        }),
    });
    web.entry = .disabled;
    web.wasi_exec_model = .reactor;
    web.root_module.export_symbol_names = &.{ "malloc", "free" };
    web.root_module.addCSourceFiles(.{
        .files = &.{
            "src/olaf_wasm.c",
            "src/pffft.c",
            "src/hash-table.c",
            "src/queue.c",
            "src/olaf_deque.c",
            "src/olaf_max_filter_perceptual_van_herk.c",
            "src/olaf_ep_extractor.c",
            "src/olaf_fp_extractor.c",
            "src/olaf_db_mem.c",
            "src/olaf_db_id.c",
            "src/olaf_fp_db_writer_mem.c",
            "src/olaf_fp_matcher.c",
            "src/olaf_config.c",
        },
        .flags = &.{ "-Wall", "-Wextra", "-Werror=return-type", "-std=gnu11" },
    });
    return web;
}

/// Add core Olaf C source files to an executable
fn addCoreSources(
    exe: *std.Build.Step.Compile,
    b: *std.Build,
    cflags: []const []const u8,
    include_lmdb: bool,
    include_olaf_main: bool,
) void {
    // Common sources used by all builds
    const common_sources = [_][]const u8{
        "src/hash-table.c",
        "src/pffft.c",
        "src/queue.c",
        "src/olaf_deque.c",
        "src/olaf_max_filter_perceptual_van_herk.c",
        "src/olaf_config.c",
        "src/olaf_db_id.c",
        "src/olaf_ep_extractor.c",
        "src/olaf_fp_db_writer_cache.c",
        "src/olaf_fp_file_writer.c",
        "src/olaf_fp_extractor.c",
        "src/olaf_fp_matcher.c",
        "src/olaf_reader_stream.c",
        "src/olaf_runner.c",
        "src/olaf_stream_processor.c",
    };

    // LMDB sources (only for native builds)
    const lmdb_sources = [_][]const u8{
        "src/mdb.c",
        "src/midl.c",
    };

    // Database implementation sources: the fp db writer is paired with the
    // matching database implementation (same pairing as the Makefile mem/web targets)
    const db_sources = [_][]const u8{
        if (include_lmdb) "src/olaf_db.c" else "src/olaf_db_mem.c",
        if (include_lmdb) "src/olaf_fp_db_writer.c" else "src/olaf_fp_db_writer_mem.c",
    };

    // Add all common sources
    for (common_sources) |src| {
        exe.root_module.addCSourceFile(.{ .file = b.path(src), .flags = cflags });
    }

    // Add LMDB sources if needed
    if (include_lmdb) {
        for (lmdb_sources) |src| {
            exe.root_module.addCSourceFile(.{ .file = b.path(src), .flags = cflags });
        }
    }

    // Add database sources
    for (db_sources) |src| {
        exe.root_module.addCSourceFile(.{ .file = b.path(src), .flags = cflags });
    }

    // Optionally add main executable source
    if (include_olaf_main) {
        exe.root_module.addCSourceFile(.{ .file = b.path("./src/olaf.c"), .flags = cflags });
    }
}

// Zig 0.16.0 has no general Zig-source prefix-map switch. @src().file is
// module-relative (Sema.zig); suppress compiler debug paths at generation time,
// and separately map every C macro/file/debug path. See docs/BUILD_PRIVACY.md.
fn applyReleasePrivacy(b: *std.Build, artifact: *std.Build.Step.Compile, cflags_file: []const u8) void {
    for (artifact.root_module.getGraph().modules) |mod| {
        mod.strip = true;
        for (mod.link_objects.items) |object| {
            const flags: *[]const []const u8 = switch (object) {
                .c_source_file => |file| &file.flags,
                .c_source_files => |files| &files.flags,
                else => continue,
            };
            var mapped = std.array_list.Managed([]const u8).init(b.allocator);
            mapped.appendSlice(flags.*) catch @panic("OOM");
            // zig_clang_driver.cpp expands GNU-style response files. The
            // Python provider creates and verifies this immutable staging input.
            mapped.append(b.fmt("@{s}", .{cflags_file})) catch @panic("OOM");
            flags.* = mapped.toOwnedSlice() catch @panic("OOM");
        }
    }
}
