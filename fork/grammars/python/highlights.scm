; Identifier naming conventions

; ((identifier) @constructor
 ; (#match? @constructor "^[A-Z]"))

; ((identifier) @constant
 ; (#match? @constant "^[A-Z][A-Z_]*$"))

; ; Builtin functions

; ((call
  ; function: (identifier) @function.builtin)
 ; (#match?
   ; @function.builtin
   ; "^(abs|all|any|ascii|bin|bool|breakpoint|bytearray|bytes|callable|chr|classmethod|compile|complex|delattr|dict|dir|divmod|enumerate|eval|exec|filter|float|format|frozenset|getattr|globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|iter|len|list|locals|map|max|memoryview|min|next|object|oct|open|ord|pow|print|property|range|repr|reversed|round|set|setattr|slice|sorted|staticmethod|str|sum|super|tuple|type|vars|zip|__import__)$"))


(decorator) @entity.name.function

(call
  function: (identifier) @entity.name.function)

(call
  function: (attribute attribute: (identifier) @entity.name.function))

(function_definition
  name: (identifier) @entity.name.function)

(class_definition
  name: (identifier) @entity.name.class)

; Literals

[
  (none)
  (true)
  (false)
] @constant.language

[
  (integer)
  (float)
] @constant.numeric

(comment) @comment
(string) @string
(escape_sequence) @escape

(interpolation
  "{" @punctuation.special
  "}" @punctuation.special) @embedded

[
  "-"
  "-="
  "!="
  "*"
  "**"
  "**="
  "*="
  "/"
  "//"
  "//="
  "/="
  "&"
  "%"
  "%="
  "^"
  "+"
  "->"
  "+="
  "<"
  "<<"
  "<="
  "<>"
  "="
  ":="
  "=="
  ">"
  ">="
  ">>"
  "|"
  "~"
  "and"
  "in"
  "is"
  "not"
  "or"
] @operator

[
  "not"
  "or"
  "and"
  "in"
  "is"
  "as"
  "assert"
  "async"
  "await"
  "break"
  "class"
  "continue"
  "def"
  "del"
  "elif"
  "else"
  "except"
  "exec"
  "finally"
  "for"
  "from"
  "global"
  "if"
  "import"
  "lambda"
  "nonlocal"
  "pass"
  "print"
  "raise"
  "return"
  "try"
  "while"
  "with"
  "yield"
  "match"
  "case"
] @keyword
