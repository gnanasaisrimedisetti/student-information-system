
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.Base64;

public class StudentSystem {

    private static final String FILE = "students.csv";

    public static void main(String[] args) {
        try {
            initializeFile();

            if (args.length == 0) {
                throw new IllegalArgumentException("Command required");
            }

            String command = args[0].toLowerCase();

            switch (command) {
                case "list":
                    printStudents();
                    break;

                case "add":
                    requireArgs(args, 6);
                    addStudent(decode(args, 1));
                    break;

                case "update":
                    requireArgs(args, 6);
                    updateStudent(decode(args, 1));
                    break;

                case "delete":
                    requireArgs(args, 2);
                    deleteStudent(decode(args, 1)[0]);
                    break;

                default:
                    throw new IllegalArgumentException(
                        "Invalid command: " + command
                    );
            }

        } catch (Exception e) {
            System.err.println(e.getMessage());
            System.exit(1);
        }
    }

    private static void requireArgs(String[] args, int count) {
        if (args.length != count) {
            throw new IllegalArgumentException(
                "Invalid number of arguments"
            );
        }
    }

    private static void initializeFile() throws IOException {
        Path path = Paths.get(FILE);
        Files.createDirectories(path.getParent());

        if (!Files.exists(path)) {
            Files.write(
                path,
                Collections.singletonList(
                    "ID,Name,Department,GPA,Email"
                ),
                StandardCharsets.UTF_8
            );
        }
    }

    private static String[] decode(String[] args, int start) {
        String[] values = new String[args.length - start];

        for (int i = start; i < args.length; i++) {
            values[i - start] = new String(
                Base64.getUrlDecoder().decode(args[i]),
                StandardCharsets.UTF_8
            );
        }

        return values;
    }

    private static List<String[]> readStudents()
            throws IOException {

        List<String[]> students = new ArrayList<>();

        List<String> lines = Files.readAllLines(
            Paths.get(FILE),
            StandardCharsets.UTF_8
        );

        for (int i = 1; i < lines.size(); i++) {
            if (!lines.get(i).trim().isEmpty()) {
                students.add(parseCsvLine(lines.get(i)));
            }
        }

        return students;
    }

    private static String[] parseCsvLine(String line) {
        List<String> values = new ArrayList<>();
        StringBuilder value = new StringBuilder();
        boolean quoted = false;

        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);

            if (c == '"') {
                if (quoted && i + 1 < line.length()
                        && line.charAt(i + 1) == '"') {
                    value.append('"');
                    i++;
                } else {
                    quoted = !quoted;
                }
            } else if (c == ',' && !quoted) {
                values.add(value.toString());
                value.setLength(0);
            } else {
                value.append(c);
            }
        }

        values.add(value.toString());
        return values.toArray(new String[0]);
    }

    private static String csv(String value) {
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }

    private static void writeStudents(List<String[]> students)
            throws IOException {

        List<String> lines = new ArrayList<>();
        lines.add("ID,Name,Department,GPA,Email");

        for (String[] s : students) {
            StringJoiner row = new StringJoiner(",");
            for (String value : s) {
                row.add(csv(value));
            }
            lines.add(row.toString());
        }

        Files.write(
            Paths.get(FILE),
            lines,
            StandardCharsets.UTF_8
        );
    }

    private static void validate(String[] s) {
        if (s.length != 5) {
            throw new IllegalArgumentException(
                "All five student fields are required"
            );
        }

        if (s[0].trim().isEmpty() || s[1].trim().isEmpty()
                || s[2].trim().isEmpty()
                || s[4].trim().isEmpty()) {
            throw new IllegalArgumentException(
                "Fields cannot be empty"
            );
        }

        double gpa;
        try {
            gpa = Double.parseDouble(s[3]);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("GPA must be numeric");
        }

        if (gpa < 0 || gpa > 10) {
            throw new IllegalArgumentException(
                "GPA must be between 0 and 10"
            );
        }

        if (!s[4].matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new IllegalArgumentException(
                "Invalid email address"
            );
        }
    }

    private static void addStudent(String[] s) throws IOException {
        validate(s);

        List<String[]> students = readStudents();

        for (String[] student : students) {
            if (student[0].equalsIgnoreCase(s[0])) {
                throw new IllegalArgumentException(
                    "Student ID already exists"
                );
            }
        }

        students.add(s);
        writeStudents(students);

        System.out.println("{\"message\":\"Student added successfully\"}");
    }

    private static void printStudents() throws IOException {
        List<String[]> students = readStudents();

        StringBuilder json = new StringBuilder("[");
        for (int i = 0; i < students.size(); i++) {
            String[] s = students.get(i);

            if (s.length != 5) continue;

            if (json.length() > 1) json.append(",");

            json.append("{")
                .append("\"id\":").append(quote(s[0])).append(",")
                .append("\"name\":").append(quote(s[1])).append(",")
                .append("\"department\":").append(quote(s[2])).append(",")
                .append("\"gpa\":").append(s[3]).append(",")
                .append("\"email\":").append(quote(s[4]))
                .append("}");
        }

        json.append("]");
        System.out.println(json);
    }

    private static String quote(String value) {
        return "\"" + value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t") + "\"";
    }

    private static void updateStudent(String[] s)
            throws IOException {

        validate(s);

        List<String[]> students = readStudents();
        boolean found = false;

        for (int i = 0; i < students.size(); i++) {
            if (students.get(i)[0].equalsIgnoreCase(s[0])) {
                students.set(i, s);
                found = true;
                break;
            }
        }

        if (!found) {
            throw new IllegalArgumentException(
                "Student ID not found"
            );
        }

        writeStudents(students);
        System.out.println("{\"message\":\"Student updated successfully\"}");
    }

    private static void deleteStudent(String id)
            throws IOException {

        List<String[]> students = readStudents();

        boolean removed = students.removeIf(
            s -> s[0].equalsIgnoreCase(id)
        );

        if (!removed) {
            throw new IllegalArgumentException(
                "Student ID not found"
            );
        }

        writeStudents(students);
        System.out.println("{\"message\":\"Student deleted successfully\"}");
    }
}
