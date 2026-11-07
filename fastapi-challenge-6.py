class Course(Base):
    __tablename__ = "courses"
    id:Mapped[int] = mapped_column(primary_key=True)
    title:Mapped[str]
    credits:Mapped[int]